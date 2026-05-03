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
            # Step 1: Navigate to login page
            step += 1
            await page.goto(BASE_URL)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: Enter username
            step += 1
            username_input = page.locator('input[name="username"], input[placeholder*="用户名"], input[type="text"]').first
            await username_input.fill('user001')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: Enter password
            step += 1
            password_input = page.locator('input[name="password"], input[placeholder*="密码"], input[type="password"]').first
            await password_input.fill('123456')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: Click login button
            step += 1
            login_button = page.locator('button:has-text("登录"), button[type="submit"], input[type="submit"]').first
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 5: Verify successful login
            step += 1
            # Check URL changed from login page
            current_url = page.url
            if 'login' in current_url.lower():
                raise Exception('登录失败：仍在登录页面')
            
            # Check for user-specific elements
            user_elements = [
                page.locator('text=个人书架'),
                page.locator('text=借阅历史'),
                page.locator('text=个人中心'),
                page.locator('text=我的'),
                page.locator('[class*="user"], [class*="profile"]')
            ]
            
            found_element = False
            for element in user_elements:
                try:
                    await expect(element).to_be_visible(timeout=5000)
                    found_element = True
                    break
                except:
                    continue
            
            if not found_element:
                # Try to find any element that indicates logged-in state
                logged_in_indicators = [
                    page.locator('text=退出'),
                    page.locator('text=注销'),
                    page.locator('text=欢迎'),
                    page.locator('[class*="logged"], [class*="auth"]')
                ]
                for indicator in logged_in_indicators:
                    try:
                        await expect(indicator).to_be_visible(timeout=3000)
                        found_element = True
                        break
                    except:
                        continue
            
            if not found_element:
                raise Exception('登录成功验证失败：未找到用户相关菜单或功能入口')
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
        finally:
            await browser.close()
    
    passed = not error_msg
    result = {
        "passed": passed, 
        "message": error_msg or '普通用户登录测试通过', 
        "steps_completed": step, 
        "steps_total": steps_total
    }
    print('###TEST_RESULT###' + json.dumps(result, ensure_ascii=False))

asyncio.run(main())