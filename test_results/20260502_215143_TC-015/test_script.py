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
    passed = False
    
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
            request_body = {
                "username": "newuser001",
                "password": "pass123456",
                "confirmPassword": "pass123456",
                "realName": "测试用户",
                "phone": "13800001111",
                "email": "newuser@test.com",
                "role": 1
            }
            
            response = await page.request.post(register_url, data=request_body)
            response_json = await response.json()
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify registration response
            step += 1
            if response.status != 200:
                raise Exception(f"HTTP状态码错误: 期望200, 实际{response.status}")
            
            if response_json.get('code') != 200:
                raise Exception(f"响应code错误: 期望200, 实际{response_json.get('code')}")
            
            if response_json.get('message') != '注册成功':
                raise Exception(f"响应message错误: 期望'注册成功', 实际{response_json.get('message')}")
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Verify login with new user
            step += 1
            login_url = f"{BASE_URL}/api/auth/login"
            login_body = {
                "username": "newuser001",
                "password": "pass123456"
            }
            
            login_response = await page.request.post(login_url, data=login_body)
            login_response_json = await login_response.json()
            
            if login_response.status != 200:
                raise Exception(f"登录HTTP状态码错误: 期望200, 实际{login_response.status}")
            
            if login_response_json.get('code') != 200:
                raise Exception(f"登录响应code错误: 期望200, 实际{login_response_json.get('code')}")
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            passed = True
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    result = {
        "passed": passed,
        "message": error_msg if error_msg else "用户注册成功测试通过",
        "steps_completed": step,
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())