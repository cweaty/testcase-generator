import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 2
    error_msg = ''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: Send POST request to login API
            step += 1
            response = await page.request.post(
                f"{BASE_URL}/api/auth/login",
                data={
                    "username": "admin",
                    "password": "123456",
                    "role": 0
                }
            )
            
            # Create a simple HTML page to display request/response for screenshot
            html_content = f"""
            <html>
            <body>
                <h2>Login API Request</h2>
                <p><strong>URL:</strong> {BASE_URL}/api/auth/login</p>
                <p><strong>Method:</strong> POST</p>
                <p><strong>Request Body:</strong></p>
                <pre>{json.dumps({"username": "admin", "password": "123456", "role": 0}, indent=2)}</pre>
                
                <h2>Response</h2>
                <p><strong>Status Code:</strong> {response.status}</p>
                <p><strong>Response Body:</strong></p>
                <pre>{await response.text()}</pre>
            </body>
            </html>
            """
            
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Verify response
            step += 1
            
            # Verify HTTP status code is 200
            if response.status != 200:
                raise AssertionError(f"Expected HTTP status 200, got {response.status}")
            
            # Parse response JSON
            response_json = await response.json()
            
            # Verify code field is 200
            if response_json.get('code') != 200:
                raise AssertionError(f"Expected code 200, got {response_json.get('code')}")
            
            # Verify data.token is not empty
            token = response_json.get('data', {}).get('token')
            if not token:
                raise AssertionError("data.token is empty or missing")
            
            # Verify data.user.role is 0
            user_role = response_json.get('data', {}).get('user', {}).get('role')
            if user_role != 0:
                raise AssertionError(f"Expected data.user.role to be 0, got {user_role}")
            
            # Update HTML with verification results
            verification_html = f"""
            <html>
            <body>
                <h2>Verification Results</h2>
                <p style="color: green;">✓ HTTP Status Code: {response.status} (Expected: 200)</p>
                <p style="color: green;">✓ Response code: {response_json.get('code')} (Expected: 200)</p>
                <p style="color: green;">✓ data.token: {token[:20]}... (Not empty)</p>
                <p style="color: green;">✓ data.user.role: {user_role} (Expected: 0)</p>
                
                <h3>Full Response Data</h3>
                <pre>{json.dumps(response_json, indent=2)}</pre>
            </body>
            </html>
            """
            
            await page.set_content(verification_html)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            try:
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
            except:
                pass
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed,
        "message": error_msg or '所有步骤通过',
        "steps_completed": step,
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())