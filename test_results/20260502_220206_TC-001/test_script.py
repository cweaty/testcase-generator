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
    response_data = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: Send POST request to login API
            step += 1
            login_url = f"{BASE_URL}/api/auth/login"
            request_body = {
                "username": "admin",
                "password": "123456",
                "role": 0
            }
            
            response = await page.request.post(
                login_url,
                data=request_body
            )
            
            # Take screenshot of request info
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Verify response
            step += 1
            
            # Verify HTTP status code
            status_code = response.status
            if status_code != 200:
                raise AssertionError(f"Expected status code 200, got {status_code}")
            
            # Parse response body
            response_data = await response.json()
            
            # Verify code field
            if response_data.get('code') != 200:
                raise AssertionError(f"Expected code 200, got {response_data.get('code')}")
            
            # Verify token is not empty
            token = response_data.get('data', {}).get('token')
            if not token:
                raise AssertionError("Token is empty or missing")
            
            # Verify user role
            user_role = response_data.get('data', {}).get('user', {}).get('role')
            if user_role != 0:
                raise AssertionError(f"Expected user role 0, got {user_role}")
            
            # Take screenshot of verification
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
    
    if response_data:
        result["response_data"] = response_data
    
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())