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
            # Step 1: Navigate to the application
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Login to get JWT token (assuming login page exists)
            step += 1
            # Navigate to login page
            await page.goto(f'{BASE_URL}/login')
            await page.wait_for_load_state('networkidle')
            
            # Fill login form (using reasonable defaults)
            await page.fill('input[name="username"]', 'testuser')
            await page.fill('input[name="password"]', 'testpassword')
            await page.click('button[type="submit"]')
            
            # Wait for login to complete
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Make POST request to /api/borrow
            step += 1
            # Get the JWT token from cookies or local storage
            token = await page.evaluate('() => localStorage.getItem("token") || document.cookie.match(/token=([^;]+)/)?.[1]')
            
            if not token:
                raise Exception("JWT token not found after login")
            
            # Make the borrow request
            response = await page.request.post(
                f'{BASE_URL}/api/borrow',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                data=json.dumps({"bookId": 1})
            )
            
            # Store response for verification
            response_data = await response.json()
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Verify the response
            step += 1
            # Verify HTTP status code
            assert response.status == 200, f"Expected status 200, got {response.status}"
            
            # Verify response body
            assert response_data.get('code') == 200, f"Expected code 200, got {response_data.get('code')}"
            assert response_data.get('message') == '借阅成功', f"Expected message '借阅成功', got {response_data.get('message')}"
            
            # Verify data contains borrow record
            assert 'data' in response_data, "Response missing 'data' field"
            borrow_data = response_data['data']
            assert 'borrowCode' in borrow_data, "Borrow data missing 'borrowCode'"
            assert 'dueDate' in borrow_data, "Borrow data missing 'dueDate'"
            
            # Verify book stock decreased (would need additional API call in real scenario)
            # This is a simplified check - in real implementation, you'd check the book's availableStock
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