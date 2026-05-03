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
            # Step 1: 发送POST请求到登录接口
            step += 1
            response = await page.request.post(
                f"{BASE_URL}/api/auth/login",
                data={
                    "username": "admin",
                    "password": "123456",
                    "role": 0
                }
            )
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 验证HTTP状态码为200
            step += 1
            status_code = response.status
            if status_code != 200:
                raise AssertionError(f"HTTP状态码验证失败: 期望200, 实际{status_code}")
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 验证响应体中code字段为200
            step += 1
            response_json = await response.json()
            code = response_json.get('code')
            if code != 200:
                raise AssertionError(f"响应体code字段验证失败: 期望200, 实际{code}")
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: 验证data.token非空且data.user.role为0
            step += 1
            data = response_json.get('data', {})
            token = data.get('token')
            user_role = data.get('user', {}).get('role')
            
            if not token:
                raise AssertionError("data.token字段为空")
            if user_role != 0:
                raise AssertionError(f"data.user.role字段验证失败: 期望0, 实际{user_role}")
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