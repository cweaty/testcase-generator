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
            # Step 1: Navigate to base URL
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Send POST request to login API
            step += 1
            api_url = f"{BASE_URL}/api/auth/login"
            request_body = {
                "username": "reader01",
                "password": "reader123",
                "role": 1
            }
            
            response = await page.request.post(api_url, data=request_body)
            
            # Verify response status code
            assert response.status == 200, f"Expected status 200, got {response.status}"
            
            # Parse response body
            response_json = await response.json()
            
            # Verify response code field
            assert response_json.get('code') == 200, f"Expected code 200, got {response_json.get('code')}"
            
            # Verify token is not empty
            token = response_json.get('data', {}).get('token')
            assert token is not None and token != '', "Token is empty or missing"
            
            # Verify user role
            user_role = response_json.get('data', {}).get('user', {}).get('role')
            assert user_role == 1, f"Expected user role 1, got {user_role}"
            
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