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
            # Step 1: 访问系统登录页面
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 输入用户名
            step += 1
            username_input = page.locator('input[name="username"], input[type="text"], #username, [data-testid="username"]')
            await username_input.fill('admin')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 输入密码
            step += 1
            password_input = page.locator('input[name="password"], input[type="password"], #password, [data-testid="password"]')
            await password_input.fill('admin123')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: 选择管理员角色
            step += 1
            role_selector = page.locator('select[name="role"], #role, [data-testid="role"], .role-select')
            await role_selector.select_option(label='管理员')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: 点击登录按钮
            step += 1
            login_button = page.locator('button[type="submit"], button:has-text("登录"), input[type="submit"], .login-btn')
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # 验证登录成功
            await expect(page).to_have_url(f'{BASE_URL}/admin/dashboard')
            await expect(page.locator('.admin-menu, .admin-panel, [data-testid="admin-menu"]')).to_be_visible()
            await expect(page.locator('.user-status, .logged-in-user, [data-testid="user-status"]')).to_contain_text('admin')
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {"passed": passed, "message": error_msg or '管理员登录测试通过', "steps_completed": step, "steps_total": steps_total}
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())