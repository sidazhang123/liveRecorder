# -*- encoding: utf-8 -*-

import gzip
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import numpy as np
import random
import cv2
from json import JSONDecodeError
from typing import Union, Dict, Any

import requests
from DrissionPage import ChromiumOptions, Chromium

from utils import trace_error_decorator, logger
from web_rid import get_sec_user_id

no_proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(no_proxy_handler)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ks_retry = 0
ks_retry_wait_time = 10
ks_slow_start = False
ks_err_log = ''


def get_req(
        url: str,
        proxy_addr: Union[str, None] = None,
        headers: Union[dict, None] = None,
        data: Union[dict, bytes, None] = None,
        json_data: Union[dict, list, None] = None,
        timeout: int = 20,
        abroad: bool = False,
        content_conding: str = 'utf-8',
        redirect_url: bool = False,
) -> Union[str, Any]:
    if headers is None:
        headers = {}
    try:
        if proxy_addr:
            proxies = {
                'http': proxy_addr,
                'https': proxy_addr
            }
            if data or json_data:
                response = requests.post(url, data=data, json=json_data, headers=headers, proxies=proxies,
                                         timeout=timeout)
            else:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            if redirect_url:
                return response.url
            resp_str = response.text
        else:
            if data and not isinstance(data, bytes):
                data = urllib.parse.urlencode(data).encode(content_conding)
            if json_data and isinstance(json_data, (dict, list)):
                data = json.dumps(json_data).encode(content_conding)

            req = urllib.request.Request(url, data=data, headers=headers)

            try:
                if abroad:
                    response = urllib.request.urlopen(req, timeout=timeout)
                else:
                    response = opener.open(req, timeout=timeout)
                if redirect_url:
                    return response.url
                content_encoding = response.info().get('Content-Encoding')
                try:
                    if content_encoding == 'gzip':
                        with gzip.open(response, 'rt', encoding=content_conding) as gzipped:
                            resp_str = gzipped.read()
                    else:
                        resp_str = response.read().decode(content_conding)
                finally:
                    response.close()

            except urllib.error.HTTPError as e:
                if e.code == 400:
                    resp_str = e.read().decode(content_conding)
                else:
                    raise
            except urllib.error.URLError as e:
                print("URL Error:", e)
                raise
            except Exception as e:
                print("An error occurred:", e)
                raise

    except Exception as e:
        resp_str = str(e)

    return resp_str


@trace_error_decorator
def get_douyin_app_stream_data(url: str, proxy_addr: Union[str, None] = None, cookies: Union[str, None] = None) -> \
        Dict[str, Any]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://live.douyin.com/',
        'Cookie': 'ttwid=1%7CB1qls3GdnZhUov9o2NxOMxxYS2ff6OSvEWbv0ytbES4%7C1680522049%7C280d802d6d478e3e78d0c807f7c487e7ffec0ae4e5fdd6a0fe74c3c6af149511; my_rd=1; passport_csrf_token=3ab34460fa656183fccfb904b16ff742; passport_csrf_token_default=3ab34460fa656183fccfb904b16ff742; d_ticket=9f562383ac0547d0b561904513229d76c9c21; n_mh=hvnJEQ4Q5eiH74-84kTFUyv4VK8xtSrpRZG1AhCeFNI; store-region=cn-fj; store-region-src=uid; LOGIN_STATUS=1; __security_server_data_status=1; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; pwa2=%223%7C0%7C3%7C0%22; download_guide=%223%2F20230729%2F0%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.6%7D; strategyABtestKey=%221690824679.923%22; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1536%2C%5C%22screen_height%5C%22%3A864%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A150%7D%22; VIDEO_FILTER_MEMO_SELECT=%7B%22expireTime%22%3A1691443863751%2C%22type%22%3Anull%7D; home_can_add_dy_2_desktop=%221%22; __live_version__=%221.1.1.2169%22; device_web_cpu_core=8; device_web_memory_size=8; xgplayer_user_id=346045893336; csrf_session_id=2e00356b5cd8544d17a0e66484946f28; odin_tt=724eb4dd23bc6ffaed9a1571ac4c757ef597768a70c75fef695b95845b7ffcd8b1524278c2ac31c2587996d058e03414595f0a4e856c53bd0d5e5f56dc6d82e24004dc77773e6b83ced6f80f1bb70627; __ac_nonce=064caded4009deafd8b89; __ac_signature=_02B4Z6wo00f01HLUuwwAAIDBh6tRkVLvBQBy9L-AAHiHf7; ttcid=2e9619ebbb8449eaa3d5a42d8ce88ec835; webcast_leading_last_show_time=1691016922379; webcast_leading_total_show_times=1; webcast_local_quality=sd; live_can_add_dy_2_desktop=%221%22; msToken=1JDHnVPw_9yTvzIrwb7cQj8dCMNOoesXbA_IooV8cezcOdpe4pzusZE7NB7tZn9TBXPr0ylxmv-KMs5rqbNUBHP4P7VBFUu0ZAht_BEylqrLpzgt3y5ne_38hXDOX8o=; msToken=jV_yeN1IQKUd9PlNtpL7k5vthGKcHo0dEh_QPUQhr8G3cuYv-Jbb4NnIxGDmhVOkZOCSihNpA2kvYtHiTW25XNNX_yrsv5FN8O6zm3qmCIXcEe0LywLn7oBO2gITEeg=; tt_scid=mYfqpfbDjqXrIGJuQ7q-DlQJfUSG51qG.KUdzztuGP83OjuVLXnQHjsz-BRHRJu4e986'
    }
    if cookies:
        headers['Cookie'] = cookies

    def get_app_data():
        room_id, sec_uid = get_sec_user_id(url=url, proxy_addr=proxy_addr)
        api2 = f'https://webcast.amemv.com/webcast/room/reflow/info/?verifyFp=verify_lxj5zv70_7szNlAB7_pxNY_48Vh_ALKF_GA1Uf3yteoOY&type_id=0&live_id=1&room_id={room_id}&sec_user_id={sec_uid}&version_code=99.99.99&app_id=1128'
        json_str2 = get_req(url=api2, proxy_addr=proxy_addr, headers=headers)
        json_data2 = json.loads(json_str2)['data']
        room_data2 = json_data2['room']
        room_data2['anchor_name'] = room_data2['owner']['nickname']
        return room_data2

    try:
        web_rid = url.split('?')[0].split('live.douyin.com/')
        if len(web_rid) > 1:
            web_rid = web_rid[1]
            api = f'https://live.douyin.com/webcast/room/web/enter/?aid=6383&app_name=douyin_web&live_id=1&device_platform=web&language=zh-CN&browser_language=zh-CN&browser_platform=Win32&browser_name=Chrome&browser_version=116.0.0.0&web_rid={web_rid}'
            json_str = get_req(url=api, proxy_addr=proxy_addr, headers=headers)
            json_data = json.loads(json_str)['data']
            room_data = json_data['data'][0]
            room_data['anchor_name'] = json_data['user']['nickname']
        else:
            room_data = get_app_data()

        if 'stream_url' not in room_data:
            raise RuntimeError('该直播类型或玩法电脑端暂未支持，请使用app端分享链接进行录制')

        if room_data['status'] == 2:
            live_core_sdk_data = room_data['stream_url']['live_core_sdk_data']
            pull_datas = room_data['stream_url']['pull_datas']
            if live_core_sdk_data:
                if pull_datas:
                    key = list(pull_datas.keys())[0]
                    json_str = pull_datas[key]['stream_data']
                else:
                    json_str = live_core_sdk_data['pull_data']['stream_data']
                json_data = json.loads(json_str)
                if 'origin' in json_data['data']:
                    origin_url_list = json_data['data']['origin']['main']
                    origin_m3u8 = {'ORIGIN': origin_url_list["hls"]}
                    origin_flv = {'ORIGIN': origin_url_list["flv"]}
                    hls_pull_url_map = room_data['stream_url']['hls_pull_url_map']
                    flv_pull_url = room_data['stream_url']['flv_pull_url']
                    room_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
                    room_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
    except Exception as e:
        room_data = {'anchor_name': ""}
    return room_data


@trace_error_decorator
def get_douyin_stream_data(url: str, proxy_addr: Union[str, None] = None, cookies: Union[str, None] = None) -> \
        Dict[str, Any]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://live.douyin.com/',
        'Cookie': 'ttwid=1%7CB1qls3GdnZhUov9o2NxOMxxYS2ff6OSvEWbv0ytbES4%7C1680522049%7C280d802d6d478e3e78d0c807f7c487e7ffec0ae4e5fdd6a0fe74c3c6af149511; my_rd=1; passport_csrf_token=3ab34460fa656183fccfb904b16ff742; passport_csrf_token_default=3ab34460fa656183fccfb904b16ff742; d_ticket=9f562383ac0547d0b561904513229d76c9c21; n_mh=hvnJEQ4Q5eiH74-84kTFUyv4VK8xtSrpRZG1AhCeFNI; store-region=cn-fj; store-region-src=uid; LOGIN_STATUS=1; __security_server_data_status=1; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; pwa2=%223%7C0%7C3%7C0%22; download_guide=%223%2F20230729%2F0%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.6%7D; strategyABtestKey=%221690824679.923%22; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1536%2C%5C%22screen_height%5C%22%3A864%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A150%7D%22; VIDEO_FILTER_MEMO_SELECT=%7B%22expireTime%22%3A1691443863751%2C%22type%22%3Anull%7D; home_can_add_dy_2_desktop=%221%22; __live_version__=%221.1.1.2169%22; device_web_cpu_core=8; device_web_memory_size=8; xgplayer_user_id=346045893336; csrf_session_id=2e00356b5cd8544d17a0e66484946f28; odin_tt=724eb4dd23bc6ffaed9a1571ac4c757ef597768a70c75fef695b95845b7ffcd8b1524278c2ac31c2587996d058e03414595f0a4e856c53bd0d5e5f56dc6d82e24004dc77773e6b83ced6f80f1bb70627; __ac_nonce=064caded4009deafd8b89; __ac_signature=_02B4Z6wo00f01HLUuwwAAIDBh6tRkVLvBQBy9L-AAHiHf7; ttcid=2e9619ebbb8449eaa3d5a42d8ce88ec835; webcast_leading_last_show_time=1691016922379; webcast_leading_total_show_times=1; webcast_local_quality=sd; live_can_add_dy_2_desktop=%221%22; msToken=1JDHnVPw_9yTvzIrwb7cQj8dCMNOoesXbA_IooV8cezcOdpe4pzusZE7NB7tZn9TBXPr0ylxmv-KMs5rqbNUBHP4P7VBFUu0ZAht_BEylqrLpzgt3y5ne_38hXDOX8o=; msToken=jV_yeN1IQKUd9PlNtpL7k5vthGKcHo0dEh_QPUQhr8G3cuYv-Jbb4NnIxGDmhVOkZOCSihNpA2kvYtHiTW25XNNX_yrsv5FN8O6zm3qmCIXcEe0LywLn7oBO2gITEeg=; tt_scid=mYfqpfbDjqXrIGJuQ7q-DlQJfUSG51qG.KUdzztuGP83OjuVLXnQHjsz-BRHRJu4e986'
    }
    if cookies:
        headers['Cookie'] = cookies

    try:
        origin_url_list = None
        html_str = get_req(url=url, proxy_addr=proxy_addr, headers=headers)
        match_json_str = re.search(r'(\{\\"state\\":.*?)]\\n"]\)', html_str)
        if not match_json_str:
            match_json_str = re.search(r'(\{\\"common\\":.*?)]\\n"]\)</script><div hidden', html_str)
        json_str = match_json_str.group(1)
        cleaned_string = json_str.replace('\\', '').replace(r'u0026', r'&')
        room_store = re.search('"roomStore":(.*?),"linkmicStore"', cleaned_string, re.S).group(1)
        anchor_name = re.search('"nickname":"(.*?)","avatar_thumb', room_store, re.S).group(1)
        room_store = room_store.split(',"has_commerce_goods"')[0] + '}}}'
        json_data = json.loads(room_store)['roomInfo']['room']
        json_data['anchor_name'] = anchor_name
        if 'status' in json_data and json_data['status'] == 4:
            return json_data

        match_json_str2 = re.findall(r'"(\{\\"common\\":.*?)"]\)</script><script nonce=', html_str)
        if match_json_str2:
            json_str = match_json_str2[1] if len(match_json_str2) > 1 else match_json_str2[0]
            json_data2 = json.loads(
                json_str.replace('\\', '').replace('"{', '{').replace('}"', '}').replace('u0026', '&'))
            if 'origin' in json_data2['data']:
                origin_url_list = json_data2['data']['origin']['main']

        else:
            html_str = html_str.replace('\\', '').replace('u0026', '&')
            match_json_str3 = re.search('"origin":\{"main":(.*?),"dash"', html_str, re.S)
            if match_json_str3:
                origin_url_list = json.loads(match_json_str3.group(1) + '}')

        if origin_url_list:
            origin_m3u8 = {'ORIGIN': origin_url_list["hls"]}
            origin_flv = {'ORIGIN': origin_url_list["flv"]}
            hls_pull_url_map = json_data['stream_url']['hls_pull_url_map']
            flv_pull_url = json_data['stream_url']['flv_pull_url']
            json_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
            json_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
        return json_data

    except Exception as e:
        logger.info(f'【dy】第一次获取数据失败：{url} ')
        return get_douyin_app_stream_data(url=url, proxy_addr=proxy_addr, cookies=cookies)


@trace_error_decorator
def identify_gap(bg, cut, bg_disp_width):
    # 参考https://hyb.life/archives/197
    # 但根据经验，对于近一半的ks图片来说有复杂区域使得matchTemplate误判（会match到x<100的点）
    # 同时根据经验移动的距离基本都在200左右(+-20)，所以找3个最可能的点里x>150的，来大幅增加命中概率
    # 读取背景图片和缺口图片
    bg_img = cv2.imread(bg)  # 背景图片
    _, bg_actual_width, _ = bg_img.shape
    cut_img = cv2.imread(cut)  # 缺口图片
    # 识别图片边缘
    bg_edge = cv2.Canny(bg_img, 100, 200)
    cut_edge = cv2.Canny(cut_img, 100, 200)
    # 转换图片格式
    bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
    cut_pic = cv2.cvtColor(cut_edge, cv2.COLOR_GRAY2RGB)
    # 边缘匹配
    matrix = cv2.matchTemplate(bg_pic, cut_pic, cv2.TM_CCOEFF_NORMED)
    matrix_copy = matrix.copy()
    # 从匹配度前三的点里随便选一个符合规范的
    top_values = []
    top_locs = []

    for _ in range(3):  # 找到前三个最大值
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(matrix_copy)
        top_values.append(maxVal)
        top_locs.append(maxLoc)
        matrix_copy[maxLoc[1], maxLoc[0]] = -999  # 假设不会出现
    # min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matrix)  # 寻找最优匹配
    for i in [coor[0] * bg_disp_width / bg_actual_width for coor in top_locs]:
        if i > 150:
            return i
    return None


def ease_out_quad(x):
    return 1 - (1 - x) * (1 - x)


def ease_out_quart(x):
    return 1 - pow(1 - x, 4)


def ease_out_expo(x):
    if x == 1:
        return 1
    else:
        return 1 - pow(2, -10 * x)


@trace_error_decorator
def get_tracks_2(distance, seconds=1, ease_func=ease_out_quart):
    # 根据轨迹离散分布生成的数学 生成  # 参考文档  https://www.jianshu.com/p/3f968958af5a
    # ks这里x轴不需要回退的假动作，但它上传的轨迹会记录y。所以在移动时对y方向加randint(-5,5)
    tracks = [0]
    offsets = [0]
    for t in np.arange(0.0, seconds, 0.1):
        ease = ease_func
        offset = round(ease(t / seconds) * distance)
        tracks.append(offset - offsets[-1])
        offsets.append(offset)
    return tracks


@trace_error_decorator
def dl_img(name, image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(name, 'wb') as f:
            f.write(response.content)


@trace_error_decorator
def get_kuaishou_stream_url(eid):
    global ks_retry, ks_slow_start, ks_err_log
    if ks_retry > 2:
        ks_retry = 0
        ks_err_log = ''
        raise Exception('ks试了3次还出错:' + ks_err_log)

    while ks_slow_start is True:
        time.sleep(20)
    ks_slow_start = True
    co = ChromiumOptions().auto_port().headless()
    # 将chrome://version中用户文件复制一份,chmod -R,使用google-chrome --user-data-dir="kwai_user_profile"通过x11打开浏览器，手动登录ks，下次再访问时可维持登陆状态
    co.set_user_data_path('kwai_user_profile')
    co.set_argument('--blink-settings=imagesEnabled=true')  # 必须加载图片过验证码
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_argument('--charset=UTF-8')
    co.incognito(False)
    page = Chromium(addr_or_opts=co).latest_tab

    page.listen.start('live.kuaishou.com/u/')
    page.get('https://live.kuaishou.com')
    time.sleep(3)

    player_container = page.ele('@class=kwai-player-container-video')
    page.actions.move_to(player_container.rect.midpoint)
    time.sleep(2)
    page.actions.move_to('进入直播间').click()
    time.sleep(5)
    # 验证码仅会在进入直播间时出，以下仅可过滑块
    if '<iframe' in page.html:
        bg = 'bg-img.png'
        slider = 'slider-img.png'
        iframe = page.get_frame(1)
        container = iframe('@class:image-container')
        slider_btn = iframe('@class=slider-btn')
        disp_width = float(container.style('width').replace('px', '').strip())
        bg_img_ele = iframe('@class=bg-img')
        dl_img(bg, bg_img_ele.attr("src"))

        slider_ele = iframe('@class=slider-img')
        slide_offset = float(slider_ele.style('left').replace('px', '').strip())
        dl_img(slider, slider_ele.attr("src"))

        print(f'display_width:{disp_width},slide_offset:{slide_offset}')
        distance = round(identify_gap(bg, slider, disp_width) - slide_offset)
        track = get_tracks_2(distance, 1, ease_out_quad)
        print(f'在页面上x轴实际要拖动：{distance}')
        print('track', track)
        page.actions.hold(slider_btn)
        for t in track:
            page.actions.move(t, random.randint(-5, 5))
            time.sleep(0.01)
        page.listen.start('kSecretApiVerify')
        page.actions.release()
        captcha_rsp = page.listen.wait()
        captcha_res = captcha_rsp.response.body
        if captcha_res['desc'] == 'ok':
            print('验证成功')
        print(captcha_res)
    time.sleep(1)
    for _ in range(3):
        page.actions.scroll(1)
        time.sleep(2)

    page.get(f'https://live.kuaishou.com/u/{eid}')
    page_source = page.listen.wait().response.body
    # 提取"playList"中的数据
    pattern = re.compile(r'window\.__INITIAL_STATE__=\s*({[^<]+?})\s*;', re.DOTALL)
    match = pattern.search(page_source)

    ks_slow_start = False
    if not match:
        page.close()

        ks_retry += 1
        ks_err_log += f'【ks】eid={eid},html中无法找到json'
        time.sleep(ks_retry * 5 + ks_retry_wait_time)
        return get_kuaishou_stream_url(eid)
    # 获取匹配的 JSON 数据
    json_data_str = match.group(1)
    json_data_str = re.sub(r'(\\u[a-zA-Z0-9]{4})', lambda x: x.group(1).encode("utf-8").decode("unicode-escape"),
                           json_data_str)
    json_data_str = json_data_str.replace(':undefined', ':"undefined"')
    json_data = json.loads(json_data_str)

    # 将 JSON 数据转换为 Python 对象

    playList = json_data.get('liveroom', {}).get('playList', [None])[-1]
    if not playList:
        page.close()

        ks_retry += 1
        ks_err_log += f'【ks】eid={eid},json->liveroom->playList失败'
        time.sleep(ks_retry * 5 + ks_retry_wait_time)
        return get_kuaishou_stream_url(eid)
    # 获取anchor_name
    anchor_name = playList.get('author', {}).get('name', '')
    anchor_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', anchor_name)

    # 获取playUrls
    playUrls = playList.get('liveStream', {}).get('playUrls', {})
    playUrls = sorted([playUrls.get('h264', {}), playUrls.get('hevc', {})], key=lambda i: len(i), reverse=True)[0]
    if len(playUrls) == 0:
        return {
            "anchor_name": anchor_name,
            "is_live": False,
            "record_url": ''
        }
    repr = playUrls.get('adaptationSet', {}).get('representation', [])
    if len(repr) == 0:
        ks_retry += 1
        ks_err_log += f'【ks】eid={eid},representation列表为空或获取异常'
        time.sleep(ks_retry * 5 + ks_retry_wait_time)
        return get_kuaishou_stream_url(eid)
    stream_url = repr[0].get('url', '')
    page.close()

    return {
        "anchor_name": anchor_name,
        "is_live": True if len(stream_url.strip()) > 0 else False,
        "record_url": stream_url
    }


@trace_error_decorator
def get_weibo_stream_data(url: str, proxy_addr: Union[str, None] = None, cookies: Union[str, None] = None) -> \
        Dict[str, Any]:
    headers = {
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cookie': 'XSRF-TOKEN=qAP-pIY5V4tO6blNOhA4IIOD; SUB=_2AkMRNMCwf8NxqwFRmfwWymPrbI9-zgzEieKnaDFrJRMxHRl-yT9kqmkhtRB6OrTuX5z9N_7qk9C3xxEmNR-8WLcyo2PM; SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9WWemwcqkukCduUO11o9sBqA; WBPSESS=Wk6CxkYDejV3DDBcnx2LOXN9V1LjdSTNQPMbBDWe4lO2HbPmXG_coMffJ30T-Avn_ccQWtEYFcq9fab1p5RR6PEI6w661JcW7-56BszujMlaiAhLX-9vT4Zjboy1yf2l',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    if cookies:
        headers['Cookie'] = cookies

    room_id = ''
    if 'show/' in url:
        room_id = url.split('?')[0].split('show/')[1]
    else:
        uid = url.split('?')[0].rsplit('/u/', maxsplit=1)[1]
        web_api = f'https://weibo.com/ajax/statuses/mymblog?uid={uid}&page=1&feature=0'
        json_str = get_req(web_api, proxy_addr=proxy_addr, headers=headers)
        try:
            json_data = json.loads(json_str)
        except JSONDecodeError:
            return None
        for i in json_data['data']['list']:
            if 'page_info' in i and i['page_info']['object_type'] == 'live':
                room_id = i['page_info']['object_id']
                break

    result = {
        "anchor_name": '',
        "is_live": False,
    }
    if room_id:
        app_api = f'https://weibo.com/l/pc/anchor/live?live_id={room_id}'
        # app_api = f'https://weibo.com/l/!/2/wblive/room/show_pc_live.json?live_id={room_id}'
        json_str = get_req(url=app_api, proxy_addr=proxy_addr, headers=headers)
        try:
            json_data = json.loads(json_str)
        except JSONDecodeError:
            return None
        anchor_name = json_data['data']['user_info']['name']
        result["anchor_name"] = anchor_name
        live_status = json_data['data']['item']['status']

        if live_status == 1:
            result["is_live"] = True
            play_url_list = json_data['data']['item']['stream_info']['pull']
            m3u8_url = play_url_list['live_origin_hls_url']
            flv_url = play_url_list['live_origin_flv_url']
            result['play_url_list'] = [
                {"m3u8_url": m3u8_url, "flv_url": flv_url},
                {"m3u8_url": m3u8_url.split('_')[0] + '.m3u8', "flv_url": flv_url.split('_')[0] + '.flv'}
            ]

    return result


if __name__ == '__main__':
    room_url = "https://live.douyin.com/745964462470"  # 抖音直播
    print(get_douyin_stream_data(room_url, proxy_addr=''))
