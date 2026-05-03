import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'your_admin_token_here')

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
            
            # Step 2: Make GET request to /api/users with authorization header
            step += 1
            response = await page.request.get(
                f'{BASE_URL}/api/users',
                headers={'Authorization': f'Bearer {ADMIN_TOKEN}'}
            )
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            # Verify HTTP status code
            assert response.status == 200, f"Expected status 200, got {response.status}"
            
            # Parse response body
            response_body = await response.json()
            
            # Verify code field
            assert response_body.get('code') == 200, f"Expected code 200, got {response_body.get('code')}"
            
            # Verify data field is array
            data = response_body.get('data')
            assert isinstance(data, list), f"Expected data to be array, got {type(data)}"
            
            # Verify each user object has required fields
            for user in data:
                assert 'id' in user, "User object missing 'id' field"
                assert 'username' in user, "User object missing 'username' field"
            
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