import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 4
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
            login_data = {
                "username": "admin",
                "password": "123456",
                "role": 0
            }
            
            response = await page.request.post(login_url, data=login_data)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify HTTP status code is 200
            step += 1
            status_code = response.status
            if status_code != 200:
                raise Exception(f"HTTP状态码不是200，实际为: {status_code}")
            
            response_json = await response.json()
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Verify response body fields
            step += 1
            # Check code field
            if response_json.get('code') != 200:
                raise Exception(f"响应体中code字段不是200，实际为: {response_json.get('code')}")
            
            # Check token field
            token = response_json.get('data', {}).get('token')
            if not token:
                raise Exception("data.token字段为空")
            
            # Check role field
            role = response_json.get('data', {}).get('user', {}).get('role')
            if role != 0:
                raise Exception(f"data.user.role字段值不是0，实际为: {role}")
            
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