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
            # Step 1: Login to get token
            step += 1
            login_response = await page.request.post(
                f"{BASE_URL}/api/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword"
                }
            )
            login_data = await login_response.json()
            assert login_response.status == 200, f"Login failed with status {login_response.status}"
            assert login_data.get("code") == 200, f"Login API returned code {login_data.get('code')}"
            token = login_data.get("data", {}).get("token")
            assert token, "No token received from login"
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Search for book
            step += 1
            search_response = await page.request.get(
                f"{BASE_URL}/api/books?keyword=三体",
                headers={"Authorization": f"Bearer {token}"}
            )
            search_data = await search_response.json()
            assert search_response.status == 200, f"Search failed with status {search_response.status}"
            assert search_data.get("code") == 200, f"Search API returned code {search_data.get('code')}"
            books = search_data.get("data", [])
            assert len(books) > 0, "No books found with keyword '三体'"
            book = next((b for b in books if b.get("id") == 1), None)
            assert book, "Book with ID 1 not found"
            assert book.get("availableStock", 0) > 0, "Book is not available for borrowing"
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Borrow the book
            step += 1
            borrow_response = await page.request.post(
                f"{BASE_URL}/api/borrow",
                data={"bookId": 1},
                headers={"Authorization": f"Bearer {token}"}
            )
            borrow_data = await borrow_response.json()
            assert borrow_response.status == 200, f"Borrow failed with status {borrow_response.status}"
            assert borrow_data.get("code") == 200, f"Borrow API returned code {borrow_data.get('code')}"
            borrow_code = borrow_data.get("data", {}).get("borrowCode")
            assert borrow_code, "No borrow code received"
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Check borrow records
            step += 1
            records_response = await page.request.get(
                f"{BASE_URL}/api/borrow/records",
                headers={"Authorization": f"Bearer {token}"}
            )
            records_data = await records_response.json()
            assert records_response.status == 200, f"Get records failed with status {records_response.status}"
            assert records_data.get("code") == 200, f"Records API returned code {records_data.get('code')}"
            records = records_data.get("data", [])
            assert len(records) > 0, "No borrow records found"
            current_record = next((r for r in records if r.get("borrowCode") == borrow_code), None)
            assert current_record, f"Record with borrow code {borrow_code} not found"
            assert current_record.get("status") == "BORROWED", f"Record status is {current_record.get('status')}, expected BORROWED"
            record_id = current_record.get("id")
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: Return the book
            step += 1
            return_response = await page.request.put(
                f"{BASE_URL}/api/borrow/{record_id}/return",
                headers={"Authorization": f"Bearer {token}"}
            )
            return_data = await return_response.json()
            assert return_response.status == 200, f"Return failed with status {return_response.status}"
            assert return_data.get("code") == 200, f"Return API returned code {return_data.get('code')}"
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 6: Verify return status
            step += 1
            verify_response = await page.request.get(
                f"{BASE_URL}/api/borrow/records",
                headers={"Authorization": f"Bearer {token}"}
            )
            verify_data = await verify_response.json()
            assert verify_response.status == 200, f"Verify records failed with status {verify_response.status}"
            assert verify_data.get("code") == 200, f"Verify API returned code {verify_data.get('code')}"
            verify_records = verify_data.get("data", [])
            returned_record = next((r for r in verify_records if r.get("id") == record_id), None)
            assert returned_record, f"Record with ID {record_id} not found after return"
            assert returned_record.get("status") == "RETURNED", f"Record status is {returned_record.get('status')}, expected RETURNED"
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed,
        "message": error_msg or "完整的图书借阅流程测试通过",
        "steps_completed": step,
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())