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
            
            # Step 2: Send POST request to register endpoint
            step += 1
            register_url = f"{BASE_URL}/api/auth/register"
            payload = {
                "username": "newreader",
                "password": "newpass123",
                "confirmPassword": "newpass123",
                "realName": "新读者",
                "phone": "13800138001",
                "email": "new@example.com",
                "role": "1"
            }
            
            response = await page.request.post(register_url, data=payload)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            status_code = response.status
            response_body = await response.json()
            
            # Verify HTTP status code
            if status_code != 200:
                raise AssertionError(f"Expected status code 200, but got {status_code}")
            
            # Verify response body
            if response_body.get('code') != 200:
                raise AssertionError(f"Expected code 200, but got {response_body.get('code')}")
            
            if response_body.get('message') != "注册成功":
                raise AssertionError(f"Expected message '注册成功', but got {response_body.get('message')}")
            
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