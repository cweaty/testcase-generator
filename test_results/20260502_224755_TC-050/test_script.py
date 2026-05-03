import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 6
    error_msg = ''
    token = None
    borrow_code = None
    record_id = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: 登录获取token
            step += 1
            login_response = await page.request.post(f'{BASE_URL}/api/auth/login', data={
                'username': 'testuser',
                'password': 'testpassword'
            })
            login_data = await login_response.json()
            if login_response.status != 200 or login_data.get('code') != 200:
                raise Exception(f'登录失败: {login_data}')
            token = login_data.get('data', {}).get('token')
            if not token:
                raise Exception('未获取到token')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 搜索图书
            step += 1
            headers = {'Authorization': f'Bearer {token}'}
            search_response = await page.request.get(f'{BASE_URL}/api/books?keyword=三体', headers=headers)
            search_data = await search_response.json()
            if search_response.status != 200 or search_data.get('code') != 200:
                raise Exception(f'搜索图书失败: {search_data}')
            
            books = search_data.get('data', [])
            book_found = False
            for book in books:
                if book.get('id') == 1 and book.get('availableStock', 0) > 0:
                    book_found = True
                    break
            if not book_found:
                raise Exception('未找到可借图书ID=1')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 借阅图书
            step += 1
            borrow_response = await page.request.post(f'{BASE_URL}/api/borrow', 
                data={'bookId': 1},
                headers=headers
            )
            borrow_data = await borrow_response.json()
            if borrow_response.status != 200 or borrow_data.get('code') != 200:
                raise Exception(f'借阅图书失败: {borrow_data}')
            borrow_code = borrow_data.get('data', {}).get('borrowCode')
            if not borrow_code:
                raise Exception('未获取到borrowCode')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: 查看借阅记录
            step += 1
            records_response = await page.request.get(f'{BASE_URL}/api/borrow/records', headers=headers)
            records_data = await records_response.json()
            if records_response.status != 200 or records_data.get('code') != 200:
                raise Exception(f'查看借阅记录失败: {records_data}')
            
            records = records_data.get('data', [])
            record_found = False
            for record in records:
                if record.get('borrowCode') == borrow_code and record.get('status') == 'BORROWED':
                    record_found = True
                    record_id = record.get('id')
                    break
            if not record_found:
                raise Exception('未找到借阅记录或状态不正确')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: 归还图书
            step += 1
            return_response = await page.request.put(f'{BASE_URL}/api/borrow/{record_id}/return', headers=headers)
            return_data = await return_response.json()
            if return_response.status != 200 or return_data.get('code') != 200:
                raise Exception(f'归还图书失败: {return_data}')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 6: 再次查看借阅记录
            step += 1
            final_records_response = await page.request.get(f'{BASE_URL}/api/borrow/records', headers=headers)
            final_records_data = await final_records_response.json()
            if final_records_response.status != 200 or final_records_data.get('code') != 200:
                raise Exception(f'再次查看借阅记录失败: {final_records_data}')
            
            final_records = final_records_data.get('data', [])
            return_record_found = False
            for record in final_records:
                if record.get('borrowCode') == borrow_code and record.get('status') == 'RETURNED':
                    return_record_found = True
                    break
            if not return_record_found:
                raise Exception('归还后记录状态未变为已归还')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed, 
        "message": error_msg or '完整的图书借阅流程测试通过', 
        "steps_completed": step, 
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())