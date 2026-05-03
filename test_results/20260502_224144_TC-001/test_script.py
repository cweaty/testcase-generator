import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 3
    error_msg = ''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: Navigate to base URL
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Send POST request to login API
            step += 1
            login_url = f"{BASE_URL}/api/auth/login"
            payload = {
                "username": "admin",
                "password": "admin123",
                "role": "0"
            }
            
            response = await page.request.post(login_url, data=payload)
            response_body = await response.json()
            
            # Save response details to a temporary page for screenshot
            await page.set_content(f"""
                <html>
                <head><title>API Response</title></head>
                <body>
                    <h1>Login API Response</h1>
                    <p><strong>URL:</strong> {login_url}</p>
                    <p><strong>Method:</strong> POST</p>
                    <p><strong>Request Body:</strong> {json.dumps(payload, indent=2)}</p>
                    <p><strong>Status Code:</strong> {response.status}</p>
                    <p><strong>Response Body:</strong></p>
                    <pre>{json.dumps(response_body, indent=2)}</pre>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            assert response.status == 200, f"Expected status 200, got {response.status}"
            assert response_body.get('code') == 200, f"Expected code 200, got {response_body.get('code')}"
            assert response_body.get('message') == 'success', f"Expected message 'success', got {response_body.get('message')}"
            
            data = response_body.get('data', {})
            assert 'token' in data, "Missing token in response data"
            assert 'userId' in data, "Missing userId in response data"
            assert 'user' in data, "Missing user in response data"
            assert data['user'].get('role') == 0, f"Expected user role 0, got {data['user'].get('role')}"
            
            # Update page with verification results
            await page.set_content(f"""
                <html>
                <head><title>Verification Results</title></head>
                <body>
                    <h1>Login API Verification Results</h1>
                    <p style="color: green;">✓ All verifications passed!</p>
                    <p><strong>Status Code:</strong> {response.status} (Expected: 200)</p>
                    <p><strong>Response Code:</strong> {response_body.get('code')} (Expected: 200)</p>
                    <p><strong>Message:</strong> {response_body.get('message')} (Expected: success)</p>
                    <p><strong>Token:</strong> Present</p>
                    <p><strong>UserId:</strong> Present</p>
                    <p><strong>User Object:</strong> Present</p>
                    <p><strong>User Role:</strong> {data['user'].get('role')} (Expected: 0)</p>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
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