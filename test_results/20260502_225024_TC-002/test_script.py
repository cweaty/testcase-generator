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
                "username": "user001",
                "password": "123456",
                "role": "1"
            }
            
            response = await page.request.post(login_url, data=payload)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Validate response
            step += 1
            status_code = response.status
            response_body = await response.json()
            
            # Validate HTTP status code
            if status_code != 200:
                raise Exception(f"HTTP状态码错误: 期望200, 实际{status_code}")
            
            # Validate response body
            if response_body.get('code') != 200:
                raise Exception(f"响应code错误: 期望200, 实际{response_body.get('code')}")
            
            if response_body.get('message') != 'success':
                raise Exception(f"响应message错误: 期望'success', 实际{response_body.get('message')}")
            
            data = response_body.get('data', {})
            if not data.get('token'):
                raise Exception("响应data中缺少token字段")
            
            if not data.get('userId'):
                raise Exception("响应data中缺少userId字段")
            
            user = data.get('user', {})
            if not user:
                raise Exception("响应data中缺少user对象")
            
            if user.get('role') != 1:
                raise Exception(f"用户角色错误: 期望1, 实际{user.get('role')}")
            
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