import os
import asyncio
import aiohttp
import requests
from bilibili_api import opus

# 异步下载图片
async def download_image(session, url, title):
    """下载图片并保存到指定目录"""
    async with session.get(url) as response:
        if response.status == 200:
            image_path = f"data/{title}/{os.path.basename(url)}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            try:
                with open(image_path, 'wb') as f:
                    f.write(await response.read())
                return os.path.basename(url)  # 返回图片文件名
            except IOError as e:
                print(f"无法保存图片 {url}: {e}")
        return None

# 获取B站用户的Opus feed
def get_opus_feed(host_mid):
    url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/opus/feed/space'
    params = {
        'host_mid': host_mid,
        'page': 1,
        'web_location': '0.0',
        'offset': '',  # 初始时 offset 为空
        'w_webid': ''
    }
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cookie': '',  # 填入你自己的cookie值
        'origin': 'https://space.bilibili.com',
        'priority': 'u=1, i',
        'referer': 'https://space.bilibili.com/{host_mid}/article',
        'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
    }

    all_opus_data = []  # 存储所有的 opus 数据

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("items", [])
            all_opus_data.extend(items)  # 将当前页的数据添加到列表中

            # 获取下一页的 offset
            params['offset'] = data.get("data", {}).get("offset", None)
            if not params['offset']:
                break  # 如果没有更多的 offset，则退出循环
        else:
            print(f"请求失败，状态码: {response.status_code}")
            break

    return all_opus_data

# 处理单个 opus 信息
async def process_opus(opus_data, session):
    opus_id = opus_data.get("opus_id")
    if not opus_id:
        return
    
    # 实例化 Opus 对象
    o = opus.Opus(opus_id)
    
    # 获取 opus 的详细数据
    try:
        data = await o.get_info()
    except Exception as e:
        print(f"Failed to retrieve data for opus_id {opus_id}: {e}")
        return

    # 调试打印407202351
    #print(f"Data for opus_id {opus_id}: {data}")  # 打印出获取到的数据以供分析

    # 解析标题和内容
    item = data.get("item", {})
    modules = item.get("modules", [])
    title = None
    content = None

    for module in modules:
        module_type = module.get("module_type")
        if module_type == "MODULE_TYPE_TITLE":
            title = module.get("module_title", {}).get("text", "Untitled")
        elif module_type == "MODULE_TYPE_CONTENT":
            content = module.get("module_content", {}).get("paragraphs", [])

    if not title or not content:
        print(f"Title or content not found for opus_id {opus_id}.")
        return

    # 创建目录
    title_dir = f"data/{title}"
    os.makedirs(title_dir, exist_ok=True)

    # 准备 Markdown 内容
    markdown_content = f"# {title}\n\n"

        # 下载图片并生成 Markdown
    for paragraph in content:
        para_type = paragraph.get("para_type")

        if para_type == 1:  # 文本段落
            text_nodes = paragraph.get("text", {}).get("nodes", [])
            if text_nodes:  # 检查是否存在 text_nodes
                for node in text_nodes:
                    # 检查节点是否具有 'word' 和 'words'
                    if 'word' in node and 'words' in node['word']:
                        markdown_content += node["word"]["words"] + "\n"
                    else:
                        print(f"节点格式不正确，跳过: {node}")

        elif para_type == 2:  # 图片段落
            pics = paragraph.get("pic", {}).get("pics", [])
            if pics:  # 检查是否存在 pics
                for pic in pics:
                    image_url = pic.get("url")
                    if image_url:
                        image_name = await download_image(session, image_url, title)
                        if image_name:
                            markdown_content += f"![Image]({image_name})\n"
                    else:
                        print(f"图片节点缺少 'url'，跳过: {pic}")

        else:
            print(f"未知的段落类型: {para_type}")


    # 保存 Markdown 文件
    markdown_file_path = os.path.join(title_dir, f"{title}.md")
    with open(markdown_file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"Markdown file created for opus_id {opus_id}: {markdown_file_path}")

# 主函数：获取 feed 并处理所有的 opus
async def main():
    # 用户输入 host_mid
    host_mid = input("请输入B站用户的主页id: ")
    
    # 获取所有 opus 数据
    opus_feed = get_opus_feed(host_mid)
    
    if not opus_feed:
        print("No Opus data found.")
        return
    
    # 使用 aiohttp 创建会话并处理 opus
    async with aiohttp.ClientSession() as session:
        tasks = [process_opus(opus_data, session) for opus_data in opus_feed]
        await asyncio.gather(*tasks)

# 运行异步主函数
asyncio.run(main())
