# -*- coding: utf-8 -*-

"""
Author: Hmily
GitHub: https://github.com/ihmily
Date: 2023-09-03 19:18:36
Update: 2024-07-01 22:16:36
Copyright (c) 2023 by Hmily, All Rights Reserved.
"""

import json
import urllib.request
from typing import Dict, Any

from utils import trace_error_decorator

no_proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(no_proxy_handler)
headers: Dict[str, str] = {'Content-Type': 'application/json'}


@trace_error_decorator
def xizhi(url: str, content: str) -> Dict[str, Any]:
    json_data = {
        'title': '直播间状态更新',
        'content': content
    }
    data = json.dumps(json_data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    response = opener.open(req, timeout=10)
    json_str = response.read().decode('utf-8')
    json_data = json.loads(json_str)
    return json_data


if __name__ == '__main__':
    content = '张三 开播了！'  # 推送内容

    # 微信推送通知
    # 替换成自己的单点推送接口,获取地址：https://xz.qqoq.net/#/admin/one
    # 当然也可以使用其他平台API 如server酱 使用方法一样
    xizhi_api = 'https://xizhi.qqoq.net/XZ2fc9ac41ace770f98a07580a6533e300.send'
    xizhi(xizhi_api, content)
