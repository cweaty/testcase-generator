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
            # Step 1: 准备请求数据
            step += 1
            token = os.environ.get('JWT_TOKEN', 'test_token_123')
            borrow_id = 100
            url = f"{BASE_URL}/api/borrow/{borrow_id}/return"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            await page.goto('about:blank')
            await page.evaluate(f'''
                () => {{
                    document.title = 'API测试准备';
                    document.body.innerHTML = '<h1>准备发送归还图书请求</h1><p>URL: {url}</p><p>借阅ID: {borrow_id}</p>';
                }}
            ''')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 2: 发送PUT请求
            step += 1
            response = await page.evaluate(f'''
                async () => {{
                    try {{
                        const response = await fetch("{url}", {{
                            method: 'PUT',
                            headers: {json.dumps(headers)},
                            body: JSON.stringify({{}})
                        }});
                        
                        const status = response.status;
                        const data = await response.json();
                        
                        return {{
                            status: status,
                            data: data,
                            success: true
                        }};
                    }} catch (error) {{
                        return {{
                            status: 0,
                            data: null,
                            success: false,
                            error: error.message
                        }};
                    }}
                }}
            ''')
            
            await page.evaluate(f'''
                () => {{
                    document.title = 'API响应结果';
                    document.body.innerHTML = `
                        <h1>归还图书API响应</h1>
                        <div style="background: #f5f5f5; padding: 20px; margin: 10px;">
                            <h3>请求信息</h3>
                            <p><strong>URL:</strong> {url}</p>
                            <p><strong>方法:</strong> PUT</p>
                            <p><strong>借阅ID:</strong> {borrow_id}</p>
                        </div>
                        <div style="background: #e8f4f8; padding: 20px; margin: 10px;">
                            <h3>响应信息</h3>
                            <p><strong>状态码:</strong> ${{response.status}}</p>
                            <p><strong>响应数据:</strong></p>
                            <pre>${{JSON.stringify(response.data, null, 2)}}</pre>
                        </div>
                    `;
                }}
            ''')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 3: 验证HTTP状态码
            step += 1
            if not response['success']:
                raise Exception(f"请求失败: {response.get('error', '未知错误')}")
            
            if response['status'] != 200:
                raise Exception(f"HTTP状态码错误: 期望200，实际{response['status']}")
            
            await page.evaluate('''
                () => {
                    const div = document.createElement('div');
                    div.style.background = '#d4edda';
                    div.style.padding = '10px';
                    div.style.margin = '10px';
                    div.innerHTML = '<h3>✅ HTTP状态码验证通过</h3><p>状态码: 200</p>';
                    document.body.appendChild(div);
                }
            ''')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
            # Step 4: 验证响应体内容
            step += 1
            response_data = response['data']
            
            if response_data.get('code') != 200:
                raise Exception(f"响应code错误: 期望200，实际{response_data.get('code')}")
            
            message = response_data.get('message', '')
            if '归还成功' not in message:
                raise Exception(f"响应message错误: 期望包含'归还成功'，实际'{message}'")
            
            # 验证借阅记录状态（假设响应中包含借阅记录信息）
            borrow_record = response_data.get('data', {}).get('borrowRecord', {})
            if borrow_record.get('status') != 1:
                raise Exception(f"借阅记录状态错误: 期望1(已归还)，实际{borrow_record.get('status')}")
            
            if not borrow_record.get('returnDate'):
                raise Exception("归还日期为空")
            
            # 验证图书库存（假设响应中包含图书信息）
            book_info = response_data.get('data', {}).get('book', {})
            if 'availableStock' not in book_info:
                raise Exception("响应中缺少availableStock字段")
            
            await page.evaluate('''
                () => {
                    const div = document.createElement('div');
                    div.style.background = '#d4edda';
                    div.style.padding = '10px';
                    div.style.margin = '10px';
                    div.innerHTML = `
                        <h3>✅ 响应体验证通过</h3>
                        <p>code: 200</p>
                        <p>message: 包含"归还成功"</p>
                        <p>借阅记录状态: 1 (已归还)</p>
                        <p>归还日期: 不为空</p>
                        <p>图书库存字段: 存在</p>
                    `;
                    document.body.appendChild(div);
                }
            ''')
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, f'step_{step:02d}.png'))
            
        except Exception as e:
            error_msg = str(e)
            await page.evaluate(f'''
                () => {{
                    const div = document.createElement('div');
                    div.style.background = '#f8d7da';
                    div.style.padding = '10px';
                    div.style.margin = '10px';
                    div.innerHTML = `<h3>❌ 测试失败</h3><p>${{error_msg}}</p>`;
                    document.body.appendChild(div);
                }}
            ''')
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