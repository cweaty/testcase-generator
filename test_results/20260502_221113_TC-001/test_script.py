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
            # Step 1: 发送POST请求到登录接口
            step += 1
            login_url = f"{BASE_URL}/api/auth/login"
            request_body = {
                "username": "admin",
                "password": "admin123",
                "role": 0
            }
            
            response = await page.request.post(
                login_url,
                data=request_body,
                headers={"Content-Type": "application/json"}
            )
            
            # 截图记录请求信息
            await page.goto("about:blank")
            await page.set_content(f"""
                <html>
                <body>
                    <h1>API请求测试</h1>
                    <p><strong>URL:</strong> {login_url}</p>
                    <p><strong>Method:</strong> POST</p>
                    <p><strong>Request Body:</strong> {json.dumps(request_body, indent=2)}</p>
                    <p><strong>Status Code:</strong> {response.status}</p>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 验证响应结果
            step += 1
            
            # 验证HTTP状态码
            assert response.status == 200, f"HTTP状态码错误，期望200，实际{response.status}"
            
            # 解析响应体
            response_json = await response.json()
            
            # 验证code字段
            assert response_json.get("code") == 200, f"响应code错误，期望200，实际{response_json.get('code')}"
            
            # 验证token字段非空
            token = response_json.get("data", {}).get("token")
            assert token is not None and token != "", "token字段为空"
            
            # 验证user.role字段
            user_role = response_json.get("data", {}).get("user", {}).get("role")
            assert user_role == 0, f"user.role字段错误，期望0，实际{user_role}"
            
            # 截图记录验证结果
            await page.set_content(f"""
                <html>
                <body>
                    <h1>API响应验证</h1>
                    <p><strong>HTTP状态码:</strong> {response.status} ✓</p>
                    <p><strong>响应code:</strong> {response_json.get('code')} ✓</p>
                    <p><strong>token:</strong> {token[:20]}... ✓</p>
                    <p><strong>user.role:</strong> {user_role} ✓</p>
                    <h2 style="color: green;">所有验证通过</h2>
                </body>
                </html>
            """)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed,
        "message": error_msg or "管理员登录成功测试通过",
        "steps_completed": step,
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())