# -*- encoding: utf-8 -*-

"""
Author: Hmily
Github:https://github.com/ihmily
Date: 2023-07-17 23:52:05
Update: 2024-03-06 23:35:00
Copyright (c) 2023 by Hmily, All Rights Reserved.
"""

import re
import urllib.request
from typing import Union

import requests

no_proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(no_proxy_handler)

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Cookie': 's_v_web_id=verify_lk07kv74_QZYCUApD_xhiB_405x_Ax51_GYO9bUIyZQVf'
}


# 获取房间ID和用户secID
def get_sec_user_id(url: str, proxy_addr: Union[str, None] = None):
    if proxy_addr:
        proxies = {
            'http': proxy_addr,
            'https': proxy_addr
        }
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
    else:
        response = opener.open(url, timeout=15)
    redirect_url = response.url
    sec_user_id = re.search(r'sec_user_id=([\w\d_\-]+)&', redirect_url).group(1)
    room_id = redirect_url.split('?')[0].rsplit('/', maxsplit=1)[1]
    return room_id, sec_user_id
