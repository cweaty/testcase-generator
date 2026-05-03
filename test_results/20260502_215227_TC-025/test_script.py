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
    token = os.environ.get('AUTH_TOKEN', 'test_token_123')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: 使用POST方法访问/api/auth/logout接口
            step += 1
            logout_url = f"{BASE_URL}/api/auth/logout"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = await page.request.post(logout_url, headers=headers)
            response_body = await response.json()
            
            # 创建一个简单的页面来显示请求和响应信息
            await page.set_content(f"""
                <html>
                <body>
                    <h2>Step 1: Logout API Request</h2>
                    <p><strong>URL:</strong> {logout_url}</p>
                    <p><strong>Method:</strong> POST</p>
                    <p><strong>Headers:</strong> Authorization: Bearer {token[:10]}...</p>
                    <h3>Response:</h3>
                    <p><strong>Status:</strong> {response.status}</p>
                    <p><strong>Body:</strong> {json.dumps(response_body, indent=2)}</p>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 验证返回HTTP状态码200和响应体中code字段为200
            step += 1
            assert response.status == 200, f"Expected status 200, got {response.status}"
            assert response_body.get('code') == 200, f"Expected code 200, got {response_body.get('code')}"
            
            await page.set_content(f"""
                <html>
                <body>
                    <h2>Step 2: Verify Logout Response</h2>
                    <p style="color: green;">✓ HTTP Status: {response.status} (Expected: 200)</p>
                    <p style="color: green;">✓ Response Code: {response_body.get('code')} (Expected: 200)</p>
                    <p>Logout successful!</p>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 使用同一token调用需认证接口返回code=401
            step += 1
            protected_url = f"{BASE_URL}/api/user/profile"  # 假设的需认证接口
            
            protected_response = await page.request.get(protected_url, headers=headers)
            protected_response_body = await protected_response.json()
            
            await page.set_content(f"""
                <html>
                <body>
                    <h2>Step 3: Verify Token Invalidation</h2>
                    <p><strong>URL:</strong> {protected_url}</p>
                    <p><strong>Method:</strong> GET</p>
                    <p><strong>Headers:</strong> Authorization: Bearer {token[:10]}...</p>
                    <h3>Response:</h3>
                    <p><strong>Status:</strong> {protected_response.status}</p>
                    <p><strong>Body:</strong> {json.dumps(protected_response_body, indent=2)}</p>
                    <p style="color: green;">✓ Response Code: {protected_response_body.get('code')} (Expected: 401)</p>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            assert protected_response_body.get('code') == 401, f"Expected code 401, got {protected_response_body.get('code')}"
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed, 
        "message": error_msg or '退出登录测试通过：状态码200，响应码200，token失效后返回401', 
        "steps_completed": step, 
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())