import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 8
    error_msg = ''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: Navigate to book management page
            step += 1
            await page.goto(f"{BASE_URL}/admin/books")
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Click "Add Book" button
            step += 1
            await page.click('button:has-text("添加图书"), button:has-text("Add Book"), [data-testid="add-book-btn"]')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Fill book title
            step += 1
            await page.fill('input[name="title"], input[placeholder*="书名"], input[placeholder*="Title"]', '测试图书A')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Fill author
            step += 1
            await page.fill('input[name="author"], input[placeholder*="作者"], input[placeholder*="Author"]', '测试作者')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: Fill ISBN
            step += 1
            await page.fill('input[name="isbn"], input[placeholder*="ISBN"]', '978-7-0000-0000-0')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 6: Fill publisher
            step += 1
            await page.fill('input[name="publisher"], input[placeholder*="出版社"], input[placeholder*="Publisher"]', '测试出版社')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 7: Select category and fill stock
            step += 1
            # Try to select category from dropdown
            try:
                await page.select_option('select[name="category"], select[placeholder*="分类"]', label='文学')
            except:
                # If dropdown not found, try filling input
                await page.fill('input[name="category"], input[placeholder*="分类"]', '文学')
            
            # Fill stock quantity
            await page.fill('input[name="stock"], input[name="quantity"], input[placeholder*="库存"], input[placeholder*="Stock"]', '10')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 8: Upload cover image and submit
            step += 1
            # Upload a test image (create a dummy file if needed)
            test_image_path = os.path.join(SCREENSHOT_DIR, 'test_cover.jpg')
            if not os.path.exists(test_image_path):
                # Create a simple test image file
                with open(test_image_path, 'wb') as f:
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t')
            
            await page.set_input_files('input[type="file"], input[name="cover"], input[name="image"]', test_image_path)
            
            # Click save/submit button
            await page.click('button:has-text("保存"), button:has-text("提交"), button:has-text("Save"), button:has-text("Submit")')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Verify success message
            success_message = page.locator('.success-message, .alert-success, [data-testid="success-message"], :text("添加成功"), :text("Added successfully")')
            await expect(success_message).to_be_visible(timeout=10000)
            
            # Verify redirect to book list or auto-refresh
            await page.wait_for_url('**/admin/books**', timeout=10000)
            await page.wait_for_load_state('networkidle')
            
            # Search for the new book in the list
            search_input = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"], input[name="search"]')
            if await search_input.count() > 0:
                await search_input.fill('测试图书A')
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
            
            # Verify book appears in list
            book_item = page.locator(':text("测试图书A"), [data-testid="book-title"]:has-text("测试图书A")')
            await expect(book_item).to_be_visible(timeout=10000)
            
            # Verify book details
            author_text = page.locator(':text("测试作者"), [data-testid="book-author"]:has-text("测试作者")')
            await expect(author_text).to_be_visible()
            
            isbn_text = page.locator(':text("978-7-0000-0000-0"), [data-testid="book-isbn"]:has-text("978-7-0000-0000-0")')
            await expect(isbn_text).to_be_visible()
            
            # Verify cover image is displayed
            cover_image = page.locator('img[src*="test_cover"], img[alt*="测试图书A"], .book-cover img')
            await expect(cover_image).to_be_visible()
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_verification.png'))
            
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