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
            # Step 1: 使用GET方法访问/api/users/profile接口
            step += 1
            token = os.environ.get('TOKEN', 'test_token')
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = await page.request.get(
                f'{BASE_URL}/api/users/profile',
                headers=headers
            )
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 验证响应结果
            step += 1
            
            # 验证HTTP状态码为200
            status_code = response.status
            assert status_code == 200, f"HTTP状态码应为200，实际为{status_code}"
            
            # 解析响应体
            response_body = await response.json()
            
            # 验证code字段为200
            assert response_body.get('code') == 200, f"响应体code字段应为200，实际为{response_body.get('code')}"
            
            # 验证返回的用户信息包含必要字段
            user_info = response_body.get('data', {})
            required_fields = ['id', 'username', 'realName']
            for field in required_fields:
                assert field in user_info, f"用户信息缺少必要字段: {field}"
            
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