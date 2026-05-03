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
    borrow_response = None
    initial_stock = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Step 1: 获取图书信息（验证前置条件）
            step += 1
            try:
                book_response = await page.request.get(f'{BASE_URL}/api/books/1')
                book_data = await book_response.json()
                initial_stock = book_data.get('data', {}).get('availableStock', 0)
                
                # 在页面上显示图书信息
                await page.set_content(f'''
                    <html>
                    <body>
                        <h1>Step {step}: 获取图书信息</h1>
                        <p>图书ID: 1</p>
                        <p>当前库存: {initial_stock}</p>
                        <p>响应状态: {book_response.status}</p>
                    </body>
                    </html>
                ''')
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
                
                if initial_stock <= 0:
                    raise Exception(f"图书库存不足，当前库存: {initial_stock}")
                    
            except Exception as e:
                error_msg = f"获取图书信息失败: {str(e)}"
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
                raise
            
            # Step 2: 发送借阅请求
            step += 1
            try:
                token = os.environ.get('JWT_TOKEN', 'test_token')
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                payload = {'bookId': 1}
                
                borrow_response = await page.request.post(
                    f'{BASE_URL}/api/borrow',
                    headers=headers,
                    data=payload
                )
                
                borrow_data = await borrow_response.json()
                
                # 在页面上显示借阅请求信息
                await page.set_content(f'''
                    <html>
                    <body>
                        <h1>Step {step}: 发送借阅请求</h1>
                        <h2>请求信息</h2>
                        <p>URL: {BASE_URL}/api/borrow</p>
                        <p>Method: POST</p>
                        <p>Headers: Authorization: Bearer {token[:10]}...</p>
                        <p>Body: {json.dumps(payload)}</p>
                        <h2>响应信息</h2>
                        <p>状态码: {borrow_response.status}</p>
                        <p>响应体: {json.dumps(borrow_data, ensure_ascii=False, indent=2)}</p>
                    </body>
                    </html>
                ''')
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
                
            except Exception as e:
                error_msg = f"发送借阅请求失败: {str(e)}"
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
                raise
            
            # Step 3: 验证借阅响应
            step += 1
            try:
                # 验证HTTP状态码
                assert borrow_response.status == 200, f"HTTP状态码不是200，而是: {borrow_response.status}"
                
                # 验证响应体结构
                assert borrow_data.get('code') == 200, f"响应code不是200，而是: {borrow_data.get('code')}"
                assert borrow_data.get('message') == '借阅成功', f"响应message不是'借阅成功'，而是: {borrow_data.get('message')}"
                assert 'data' in borrow_data, "响应中缺少data字段"
                
                # 验证data字段包含必要信息
                borrow_record = borrow_data['data']
                assert 'borrowCode' in borrow_record, "借阅记录中缺少borrowCode"
                assert 'dueDate' in borrow_record, "借阅记录中缺少dueDate"
                
                # 在页面上显示验证结果
                await page.set_content(f'''
                    <html>
                    <body>
                        <h1>Step {step}: 验证借阅响应</h1>
                        <h2>验证结果</h2>
                        <p>✅ HTTP状态码: {borrow_response.status}</p>
                        <p>✅ 响应code: {borrow_data.get('code')}</p>
                        <p>✅ 响应message: {borrow_data.get('message')}</p>
                        <p>✅ 借阅编码: {borrow_record.get('borrowCode')}</p>
                        <p>✅ 到期日期: {borrow_record.get('dueDate')}</p>
                    </body>
                    </html>
                ''')
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
                
            except Exception as e:
                error_msg = f"验证借阅响应失败: {str(e)}"
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
                raise
            
            # Step 4: 验证图书库存减少
            step += 1
            try:
                # 重新获取图书信息
                book_response_after = await page.request.get(f'{BASE_URL}/api/books/1')
                book_data_after = await book_response_after.json()
                current_stock = book_data_after.get('data', {}).get('availableStock', 0)
                
                # 验证库存减少1
                expected_stock = initial_stock - 1
                assert current_stock == expected_stock, f"库存未减少1，期望: {expected_stock}，实际: {current_stock}"
                
                # 在页面上显示库存验证结果
                await page.set_content(f'''
                    <html>
                    <body>
                        <h1>Step {step}: 验证图书库存减少</h1>
                        <h2>库存变化</h2>
                        <p>借阅前库存: {initial_stock}</p>
                        <p>借阅后库存: {current_stock}</p>
                        <p>期望库存: {expected_stock}</p>
                        <p>✅ 库存减少1</p>
                    </body>
                    </html>
                ''')
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
                
            except Exception as e:
                error_msg = f"验证图书库存减少失败: {str(e)}"
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}_error.png'))
                raise
                
        except Exception as e:
            if not error_msg:
                error_msg = str(e)
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