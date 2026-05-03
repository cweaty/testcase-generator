import os
import asyncio
import json
from playwright.async_api import async_playwright, expect

SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', '.')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5173')
TIMEOUT = int(os.environ.get('TIMEOUT', '30000'))

async def main():
    step = 0
    steps_total = 5
    error_msg = ''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: 打开浏览器，访问系统登录页面
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 在用户名输入框输入 admin
            step += 1
            username_input = page.locator('input[name="username"], input[type="text"], input[placeholder*="用户名"], input[placeholder*="账号"]')
            await username_input.fill('admin')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 在密码输入框输入 admin123
            step += 1
            password_input = page.locator('input[name="password"], input[type="password"], input[placeholder*="密码"]')
            await password_input.fill('admin123')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: 点击“登录”按钮
            step += 1
            login_button = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Login"), input[type="submit"]')
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: 验证登录成功
            step += 1
            # 验证页面跳转（URL不再是登录页面）
            current_url = page.url
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                raise Exception(f'登录后仍在登录页面: {current_url}')
            
            # 验证页面显示管理员相关的菜单或功能入口
            admin_elements = page.locator('text=管理员, text=后台, text=管理, text=Admin, text=Dashboard, text=控制台')
            await expect(admin_elements.first).to_be_visible(timeout=10000)
            
            # 验证用户状态显示为已登录的管理员
            user_status = page.locator('text=admin, text=管理员, text=欢迎, text=退出, text=注销, text=登录成功')
            await expect(user_status.first).to_be_visible(timeout=10000)
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed,
        "message": error_msg or '管理员登录测试通过',
        "steps_completed": step,
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())