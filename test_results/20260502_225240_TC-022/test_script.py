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
            
            # Step 2: Send GET request to /api/books with keyword=三体
            step += 1
            response = await page.request.get(f"{BASE_URL}/api/books", params={"keyword": "三体"})
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            status = response.status
            response_json = await response.json()
            
            # Verify HTTP status code
            if status != 200:
                raise AssertionError(f"HTTP状态码不是200，实际为: {status}")
            
            # Verify response body
            if response_json.get('code') != 200:
                raise AssertionError(f"响应体中code字段不是200，实际为: {response_json.get('code')}")
            
            records = response_json.get('data', {}).get('records', [])
            if not records:
                raise AssertionError("data.records数组为空")
            
            # Check if any record contains "三体" in title
            has_santi = False
            for record in records:
                if '三体' in record.get('title', ''):
                    has_santi = True
                    break
            
            if not has_santi:
                raise AssertionError("data.records中没有包含'三体'的图书记录")
            
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