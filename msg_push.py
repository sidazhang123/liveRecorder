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
def xizhi(url: str, content: str, title: str) -> Dict[str, Any]:
    json_data = {
        'title': title,
        'content': content
    }
    data = json.dumps(json_data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    response = opener.open(req, timeout=10)
    json_str = response.read().decode('utf-8')
    json_data = json.loads(json_str)
    return json_data


