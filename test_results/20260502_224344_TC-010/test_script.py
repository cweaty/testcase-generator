import os
import asyncio
import json
from playwright.async_api import async_playwright

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
            
            # Step 2: Send POST request to register API
            step += 1
            register_url = f"{BASE_URL}/api/auth/register"
            request_body = {
                "username": "newreader",
                "password": "newpass123",
                "confirmPassword": "newpass123",
                "realName": "新读者",
                "phone": "13800138001",
                "email": "new@example.com",
                "role": "1"
            }
            
            response = await page.request.post(
                register_url,
                data=request_body
            )
            
            # Store response details for verification
            status_code = response.status
            response_text = await response.text()
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Verify response
            step += 1
            try:
                response_json = json.loads(response_text)
                code = response_json.get('code')
                message = response_json.get('message')
                
                if status_code != 200:
                    raise AssertionError(f"Expected status code 200, got {status_code}")
                
                if code != 200:
                    raise AssertionError(f"Expected code 200, got {code}")
                
                if message != "注册成功":
                    raise AssertionError(f"Expected message '注册成功', got '{message}'")
                
                # Display success message on page
                await page.set_content(f"""
                    <html>
                    <body>
                        <h1>注册成功</h1>
                        <p>状态码: {status_code}</p>
                        <p>响应码: {code}</p>
                        <p>消息: {message}</p>
                    </body>
                    </html>
                """)
                
            except json.JSONDecodeError:
                raise AssertionError(f"Failed to parse response as JSON: {response_text}")
            
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