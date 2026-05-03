import os
import asyncio
import json
from playwright.async_api import async_playwright

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
                    "username": "reader01",
                    "password": "reader123",
                    "role": 1
                }
            )
            
            # Capture response details for screenshot
            response_text = await response.text()
            response_json = await response.json()
            
            # Create a simple HTML page to display the response for screenshot
            html_content = f"""
            <html>
            <head><title>Login API Response</title></head>
            <body>
                <h1>Login API Response</h1>
                <h2>HTTP Status: {response.status}</h2>
                <h2>Response Body:</h2>
                <pre>{response_text}</pre>
            </body>
            </html>
            """
            await page.set_content(html_content)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Verify response
            step += 1
            
            # Verify HTTP status code
            if response.status != 200:
                raise Exception(f"HTTP status code is {response.status}, expected 200")
            
            # Verify response body code field
            if response_json.get("code") != 200:
                raise Exception(f"Response code is {response_json.get('code')}, expected 200")
            
            # Verify data.token is not empty
            token = response_json.get("data", {}).get("token")
            if not token:
                raise Exception("data.token is empty")
            
            # Verify data.user.role is 1
            user_role = response_json.get("data", {}).get("user", {}).get("role")
            if user_role != 1:
                raise Exception(f"data.user.role is {user_role}, expected 1")
            
            # Update HTML with verification results
            html_content = f"""
            <html>
            <head><title>Verification Results</title></head>
            <body>
                <h1>Verification Results</h1>
                <h2>HTTP Status: {response.status} ✓</h2>
                <h2>Response Code: {response_json.get('code')} ✓</h2>
                <h2>Token: {token[:20]}... ✓</h2>
                <h2>User Role: {user_role} ✓</h2>
                <h2>All verifications passed!</h2>
            </body>
            </html>
            """
            await page.set_content(html_content)
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