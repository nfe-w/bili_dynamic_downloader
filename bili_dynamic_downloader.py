# !/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Description: 用户全量动态爬取
#
# @Author: nfe-w
# @Time: 2022-10-11 18:05

import asyncio
import json
import os
import time

import aiohttp
from bilibili_api import user

uid = 672328094  # 用户uid
need_download = True  # 是否下载动态
skip_forward_and_video = True  # 是否跳过转发动态和视频投稿的封面
skip_text_only = True  # 是否跳过纯文字动态

if not uid:
    exit(1)
u = user.User(uid=uid)

semaphore = 50  # 并发量


def get_item_info(card_info):
    if 'item' in card_info:
        return get_item_info(card_info['item'])

    if 'videos' in card_info:
        return {
            'title': card_info.get('title'),
            'desc': card_info.get('desc'),
            'dynamic': card_info.get('dynamic'),
            'short_link': card_info.get('short_link'),
            'stat': card_info.get('stat'),
            'tname': card_info.get('tname'),
            'av': card_info.get('aid'),
            'pictures': [card_info.get('pic')],
        }
    else:
        return {
            'description': card_info.get('description'),
            'content': card_info.get('content'),
            'pictures': [] if card_info.get('pictures') is None else [pic['img_src'] for pic in card_info.get('pictures')],
        }


async def get_all_json(obj_array):
    offset = 0
    while True:
        print(f'fetch, offset->{offset}')
        res = await u.get_dynamics(offset)
        if res['has_more'] != 1:
            break
        offset = res['next_offset']
        for card in res['cards']:
            # 提取主要信息
            card_main_info = {
                'dynamic_id': card['desc']['dynamic_id'],
                'timestamp': card['desc']['timestamp'],
                'type': card['desc']['type'],
                'item': get_item_info(card['card'])
            }
            if 'origin' in card['card']:
                origin_obj = json.loads(card['card']['origin'])
                card_main_info['origin'] = get_item_info(origin_obj)
                if 'user' in origin_obj and 'name' in origin_obj['user']:
                    card_main_info['origin_user'] = origin_obj['user']['name']

            obj_array.append(card_main_info)


async def download_with_aiohttp(sem, pic_url, file_name, save_dir, client):
    async with sem:
        file_path = os.path.join(save_dir, file_name)
        if os.path.isfile(file_path):
            print(f'---{file_path} already exist...\r')
        else:
            print(f'---{file_path} downloading...\r')
            async with client.get(pic_url) as response:
                if response.status == 200:
                    content = await response.content.read()
                    await asyncio.sleep(0)
                    if content:
                        with open(file_path, 'wb') as f:
                            f.write(content)


def get_headers():
    return {
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': f'https://space.bilibili.com/{uid}/dynamic',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36'
    }


async def async_main(pic_info_list):
    sem = asyncio.Semaphore(semaphore)
    async with aiohttp.ClientSession(headers=get_headers()) as client:
        tasks = [download_with_aiohttp(sem, pic_info_list[i]['url'], pic_info_list[i]['url'].split('/').pop(), pic_info_list[i]['save_dir'], client) for i in
                 range(len(pic_info_list))]
        return await asyncio.gather(*tasks)


def download_pic(save_dir, obj_array):
    download_base = save_dir + '/dynamic'
    os.makedirs(download_base, exist_ok=True)
    pic_info_list = []

    for item in obj_array:
        if skip_forward_and_video and (item['type'] == 1 or item['type'] == 8):
            # 跳过转发、投稿的封面
            continue

        pictures = item['item']['pictures']
        if skip_text_only and len(pictures) == 0:
            # 跳过纯文字动态
            continue

        current_dynamic_base = download_base + '/' + time.strftime("%Y-%m-%d_%H%M%S", time.localtime(item['timestamp']))
        os.makedirs(current_dynamic_base, exist_ok=True)

        if item['item']['content'] is not None:
            with open(current_dynamic_base + '/content.txt', 'w', encoding='UTF-8') as f:
                f.write(item['item']['content'])
                f.flush()
        if item['item']['description'] is not None:
            with open(current_dynamic_base + '/description.txt', 'w', encoding='UTF-8') as f:
                f.write(item['item']['description'])
                f.flush()

        for url in pictures:
            pic_info_list.append({
                'url': url,
                'save_dir': current_dynamic_base,
            })

    print(f'===> 开始下载图片...数量: {len(pic_info_list)}')
    asyncio.run(async_main(pic_info_list))
    print(f'===> 图片(数量: {len(pic_info_list)})已全部下载完毕，下方如有警告可忽略')


def real_main():
    save_dir = f'./dynamic_download/{uid}'
    os.makedirs(save_dir, exist_ok=True)

    obj_array = []
    asyncio.get_event_loop().run_until_complete(get_all_json(obj_array))
    with open(save_dir + '/result.json', 'w', encoding='UTF-8') as f:
        f.write(json.dumps(obj_array, ensure_ascii=False))
        f.flush()
    print('===> 获取全部json完毕')
    if need_download:
        download_pic(save_dir, obj_array)


if __name__ == '__main__':
    real_main()
