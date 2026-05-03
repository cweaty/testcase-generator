import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))
TOKEN = os.environ.get('JWT_TOKEN', 'your_jwt_token_here')

async def main():
    step = 0
    steps_total = 3
    error_msg = ''
    response_data = None
    
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
            
            # Step 2: Send PUT request to return book
            step += 1
            headers = {
                'Authorization': f'Bearer {TOKEN}',
                'Content-Type': 'application/json'
            }
            
            response = await page.request.put(
                f'{BASE_URL}/api/borrow/100/return',
                headers=headers
            )
            
            response_data = await response.json()
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            assert response.status == 200, f"HTTP状态码不是200，实际为{response.status}"
            assert response_data.get('code') == 200, f"响应code不是200，实际为{response_data.get('code')}"
            assert '归还成功' in response_data.get('message', ''), f"响应message不包含'归还成功'，实际为{response_data.get('message')}"
            
            # Check returnDate is not empty
            borrow_record = response_data.get('data', {})
            if borrow_record:
                assert borrow_record.get('returnDate'), "returnDate为空"
                assert borrow_record.get('status') == 1, f"借阅状态不是1（已归还），实际为{borrow_record.get('status')}"
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    message = error_msg if error_msg else '图书归还成功，所有验证通过'
    
    result = {
        "passed": passed,
        "message": message,
        "steps_completed": step,
        "steps_total": steps_total
    }
    
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())