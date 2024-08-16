# -*- encoding: utf-8 -*-
from __future__ import annotations

import configparser
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from datetime import datetime, date
from typing import Any, Union, Dict

from chinese_calendar import is_workday, is_holiday

from msg_push import xizhi
from spider import (
    get_douyin_stream_data,
    get_kuaishou_stream_url,
    get_weibo_stream_data,
)
from utils import  trace_error_decorator
from logger import logger

class ThreadSafeSet:
    def __init__(self):
        self._set = set()
        self._lock = threading.Lock()

    def add(self, item):
        with self._lock:
            self._set.add(item)

    def discard(self, item):
        with self._lock:
            self._set.discard(item)

    def __contains__(self, item):
        with self._lock:
            return item in self._set

    def __iter__(self):
        with self._lock:
            return iter(self._set.copy())

    def __str__(self):
        return f'{self._set}'

    def size(self):
        with self._lock:
            return len(self._set)


# 全局错误数，用于调整同时开启的monitor线程数以及每个线程中循环的次数。其实监控少量的情况下没啥作用
warning_count = 0
max_request = 0
# 让主循环扫timeline时不要重复触发monitor
monitoring = ThreadSafeSet()
# 纯display_info展示正在录像用
recording = ThreadSafeSet()
# dict{H:OrderedDict{(开始监控的时间，监控时长):(video_quality,url,主播name, monitor_interval,mon_countdown),...}
#      W:OrderedDict{(开始监控的时间，监控时长):(video_quality,url,主播name, monitor_interval,mon_countdown),...}
# “开始监控的时间”为从当日0点开始的毫秒数
monitor_timeline_w_record_params = dict()
script_path = os.path.split(os.path.realpath(sys.argv[0]))[0]
config_file = f'{script_path}/config/config.ini'
url_config_file = f'{script_path}/config/URL_config.ini'
backup_dir = f'{script_path}/backup_config'
encoding = 'utf-8-sig'
rstr = r"[\/\\\:\*\?\"\<\>\|&.。,， ]"
ffmpeg_path = f"{script_path}/ffmpeg.exe"
default_path = f'{script_path}/downloads'
os.makedirs(default_path, exist_ok=True)
file_update_lock = threading.Lock()


def signal_handler(_signal, _frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)


def display_info(disp_interval: int):
    if len(video_save_path) > 0 and not os.path.exists(video_save_path):
        logger.error("【config.ini】'直播保存路径（不填则默认）'路径不存在，留空使用默认值/liverRecorder/downloads。退出")
        sys.exit(0)
    time.sleep(20)
    while True:
        try:
            now_time = datetime.now()
            if 1<=now_time.hour<=10: continue

            rec_size = recording.size()
            lg = f"【扫描】监测{monitoring.size()}个直播中|{rec_size}个正在录像|"
            if rec_size > 0:
                for recording_live in recording:
                    author_name, start_rec_time = recording_live
                    rec_elapsed = now_time - start_rec_time
                    hours, remainder = divmod(rec_elapsed.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    lg += f"[{author_name}] 已录{hours:02d}:{minutes:02d}:{seconds:02d}|"
            lg += f"目前错误数为: {warning_count}"
            logger.info(lg)
        except Exception as e:
            logger.error(f"【错误信息】{e} 发生错误的行数: {e.__traceback__.tb_lineno}")
        time.sleep(disp_interval)


def update_file(file_path: str, old_str: str, new_str: str, start_str: str = None):
    # 如果待更新的new_str 和 已有的 old_str 没区别，并且 不需要使用注释(start_str)，则直接返回
    if old_str == new_str and start_str is None:
        return
    with file_update_lock:
        file_data = ""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            for text_line in f:
                if old_str in text_line:
                    text_line = text_line.replace(old_str, new_str)
                    if start_str:
                        text_line = f'{start_str}{text_line}'
                file_data += text_line
        with open(file_path, "w", encoding="utf-8-sig") as f:
            f.write(file_data)


def converts_mp4(address: str):
    if ts_to_mp4:
        _output = subprocess.check_output([
            "ffmpeg", "-i", address,
            "-c:v", "copy",
            "-c:a", "copy",
            "-f", "mp4", address.split('.')[0] + ".mp4",
        ], stderr=subprocess.STDOUT)
        if delete_origin_file:
            time.sleep(1)
            if os.path.exists(address):
                os.remove(address)


def change_max_connect():
    global max_request
    global warning_count
    preset = max_request
    start_time = time.time()

    while True:
        time.sleep(5)
        if 10 <= warning_count <= 20:
            if preset > 5:
                max_request = 5
            else:
                max_request //= 2
                if max_request > 0:
                    max_request = preset
                else:
                    preset = 1

            warning_count = 0
            time.sleep(5)

        elif 20 < warning_count:
            max_request = 1
            warning_count = 0
            time.sleep(10)

        elif warning_count < 10 and time.time() - start_time > 60:
            max_request = preset
            warning_count = 0
            start_time = time.time()


@trace_error_decorator
def get_douyin_stream_url(json_data: dict, video_quality: str) -> Dict[str, Any]:
    anchor_name = json_data.get('anchor_name', None)
    result = {
        "anchor_name": anchor_name,
        "is_live": False,
    }
    status = json_data.get("status", 4)  # 直播状态 2 是正在直播、4 是未开播
    if status == 2:
        stream_url = json_data['stream_url']
        flv_url_dict = stream_url['flv_pull_url']
        flv_url_list = list(flv_url_dict.values())
        m3u8_url_dict = stream_url['hls_pull_url_map']
        m3u8_url_list = list(m3u8_url_dict.values())

        while len(flv_url_list) < 5:
            flv_url_list.append(flv_url_list[-1])
            m3u8_url_list.append(m3u8_url_list[-1])

        video_qualities = {"原画": 0, "蓝光": 0, "超清": 1, "高清": 2, "标清": 3, "流畅": 4}
        quality_index = video_qualities.get(video_quality)
        m3u8_url = m3u8_url_list[quality_index]
        flv_url = flv_url_list[quality_index]
        result['m3u8_url'] = m3u8_url
        result['flv_url'] = flv_url
        result['is_live'] = True
        result['record_url'] = m3u8_url
    return result


@trace_error_decorator
def get_stream_url(json_data: dict, video_quality: str, url_type: str = 'm3u8', spec: bool = False,
                   extra_key: Union[str, int] = None) -> Dict[str, Any]:
    if not json_data['is_live']:
        return json_data

    play_url_list = json_data['play_url_list']
    quality_list = {'原画': 0, '蓝光': 0, '超清': 1, '高清': 2, '标清': 3, '流畅': 4}
    while len(play_url_list) < 5:
        play_url_list.append(play_url_list[-1])

    selected_quality = quality_list[video_quality]
    data = {
        "anchor_name": json_data['anchor_name'],
        "is_live": True
    }
    if url_type == 'm3u8':
        m3u8_url = play_url_list[selected_quality][extra_key] if extra_key else play_url_list[selected_quality]
        data["m3u8_url"] = json_data['m3u8_url'] if spec else m3u8_url
        data["record_url"] = m3u8_url
    else:
        flv = play_url_list[selected_quality][extra_key] if extra_key else play_url_list[selected_quality]
        data["flv_url"] = flv
        data["record_url"] = flv

    return data


def push_message(content: str) -> Union[str, list]:
    push_pts = []
    if '微信' in live_status_push:
        push_pts.append('微信')
        xizhi(xizhi_api_url, content)
    push_pts = '、'.join(push_pts) if len(push_pts) > 0 else []
    return push_pts


def start_monitor_n_record(url_params: list, monitoring_set: ThreadSafeSet):
    global warning_count
    global video_save_path
    start_pushed = False
    record_quality, record_url, author_name, mon_interval, mon_countdown = url_params
    monitoring_set.add(record_url)
    interruption_prob = False
    count_time = time.time()
    logger.info(f"【扫描】{author_name} 开始监控")
    while True:
        rec_triggered = False
        # 获取串流地址（检测是否开播）、推送开关播信息、录制开始
        try:
            if 'live.douyin.com' in record_url:
                platform = '抖音直播'
                with semaphore:
                    json_data = get_douyin_stream_data(url=record_url, cookies=dy_cookie)
                    port_info = get_douyin_stream_url(json_data, record_quality)
            elif 'live.kuaishou.com' in record_url:
                platform = '快手直播'
                with semaphore:
                    port_info = get_kuaishou_stream_url(eid=record_url.split('?')[0].split('/')[-1])
            elif 'weibo.com' in record_url:
                platform = '微博直播'
                with semaphore:
                    json_data = get_weibo_stream_data(
                        url=record_url, cookies=weibo_cookie)
                    port_info = get_stream_url(json_data, record_quality, extra_key='m3u8_url')
            else:
                logger.error(f'【URLconfig.ini】{record_url} 未知直播地址')
                monitoring_set.discard(record_url)
                return
            # anchor_name仅用来检测获取成功与否，不改了。但主播名字用从配置文件中获取的author_name替代
            # port_info为None出自kuaishou，get不到anchor出自其他
            if not port_info:
                raise Exception(f'{author_name} 直播间html解析失败,重试中.地址:{record_url}')
            # 开关播推送信息
            push_at = datetime.today().strftime('%m-%d %H:%M:%S')
            if port_info['is_live'] is False:
                logger.info(f"【扫描】{author_name} 未开播，等待中... ")
                if start_pushed and over_show_push:
                    push_content = f"直播间状态更新：[直播间名称] 直播已结束！时间：[时间]"
                    push_content = push_content.replace('[直播间名称]', author_name).replace('[时间]',
                                                                                             push_at)
                    push_pts = push_message(push_content.replace(r'\n', '\n'))
                    if push_pts:
                        logger.info(f'【推送】已推送[{author_name}]下播状态')
                start_pushed = False
            else:
                logger.info(f"【扫描】{author_name} 开播啦 ")
                if live_status_push and not start_pushed:
                    if begin_show_push:
                        push_content = f"直播间状态更新：[直播间名称] 正在直播中，时间：[时间]"
                        push_content = push_content.replace('[直播间名称]', author_name).replace('[时间]',
                                                                                                 push_at)
                        push_pts = push_message(push_content.replace(r'\n', '\n'))
                        if push_pts:
                            logger.info(f'【推送】已推送[{author_name}]开播状态')
                    start_pushed = True
            # 开始录像
            if port_info['is_live'] is True:
                # 串流地址
                real_url = port_info['record_url']
                if len(real_url) == 0:
                    raise Exception(f'{author_name}返回串流地址为空。')
                # 录像保存路径
                full_path = f'{default_path}/{platform}'
                # 剔除不合规字符以用于保存路径
                author_name = re.sub(rstr, "_", author_name)
                # 文件系统中创建保存路径
                try:
                    if len(video_save_path) > 0:
                        if video_save_path[-1] not in ["/", "\\"]:
                            video_save_path = video_save_path + "/"
                        full_path = f'{video_save_path}{platform}'
                    full_path = full_path.replace("\\", '/')
                    if folder_by_author:
                        full_path = f'{full_path}/{author_name}'
                    if not os.path.exists(full_path):
                        os.makedirs(full_path)
                except Exception as e:
                    logger.error(f"【错误信息】{e} 发生错误的行数: {e.__traceback__.tb_lineno}")
                if not os.path.exists(full_path):
                    logger.error(
                        f"【错误信息】{full_path}生成的录像保存路径不存在，检查URLconfig.ini填写的主播名及main.py 311-317行处理逻辑")
                # ffmpeg参数
                user_agent = ("Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 ("
                              "KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile "
                              "Safari/537.36")
                analyzeduration = "20000000"
                probesize = "10000000"
                bufsize = "8000k"
                max_muxing_queue_size = "1024"
                # 串流地址在这个cmd里了
                ffmpeg_command = [
                    'ffmpeg', "-y",
                    "-v", "verbose",
                    "-rw_timeout", "30000000",
                    "-loglevel", "error",
                    "-hide_banner",
                    "-user_agent", user_agent,
                    "-protocol_whitelist", "rtmp,crypto,file,http,https,tcp,tls,udp,rtp",
                    "-thread_queue_size", "1024",
                    "-analyzeduration", analyzeduration,
                    "-probesize", probesize,
                    "-fflags", "+discardcorrupt",
                    "-i", real_url,
                    "-bufsize", bufsize,
                    "-sn", "-dn",
                    "-reconnect_delay_max", "60",
                    "-reconnect_streamed", "-reconnect_at_eof",
                    "-max_muxing_queue_size", max_muxing_queue_size,
                    "-correct_ts_overflow", "1",
                ]
                # recording只是给displayinfo用，(author_name,start_record_time)即可
                now = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
                rec_name_time = (author_name, datetime.now())
                recording.add(rec_name_time)
                # 附加录制参数
                if video_save_type == "MP4":
                    if split_video_by_time:
                        command = [
                            "-c:v", "copy",
                            "-c:a", "aac",
                            "-map", "0",
                            "-f", "segment",
                            "-segment_time", split_time,
                            "-segment_format", "mp4",
                            "-reset_timestamps", "1",
                            f"{full_path}/{author_name}_{now}_%03d.mp4",
                        ]
                    else:
                        command = [
                            "-map", "0",
                            "-c:v", "copy",
                            "-c:a", "copy",
                            "-f", "mp4",
                            f"{full_path}/{author_name}_{now}.mp4",
                        ]
                elif video_save_type == "TS音频":
                    if split_video_by_time:
                        command = [
                            "-map", "0:a",
                            "-c:a", 'copy',
                            "-f", "segment",
                            "-segment_time", split_time,
                            "-segment_format", 'mpegts',
                            "-reset_timestamps", "1",
                            f"{full_path}/{author_name}_{now}_%03d.{'mp3' if ts_to_mp3 else 'ts'}",
                        ]
                    else:
                        command = [
                            "-map", "0:a",
                            "-c:a", "copy",
                            "-f", "mpegts",
                            f"{full_path}/{author_name}_{now}.ts"
                        ]
                else:
                    if split_video_by_time:
                        command = [
                            "-c:v", "copy",
                            "-c:a", 'copy',
                            "-map", "0",
                            "-f", "segment",
                            "-segment_time", split_time,
                            "-segment_format", 'mp4' if ts_to_mp4 else 'mpegts',
                            "-reset_timestamps", "1",
                            f"{full_path}/{author_name}_{now}_%03d.{'mp4' if ts_to_mp4 else 'ts'}"
                        ]
                    else:
                        command = [
                            "-c:v", "copy",
                            "-c:a", "copy",
                            "-map", "0",
                            "-f", "mpegts",
                            f"{full_path}/{author_name}_{now}.ts",
                        ]
                try:
                    ffmpeg_command.extend(command)
                    _output = subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT)
                    rec_triggered = True
                    interruption_prob = False
                    logger.info(f"【录像】{author_name} 直播录制完成")
                    recording.discard(rec_name_time)
                except subprocess.CalledProcessError as e:
                    logger.error(
                        f"【录像】{author_name} 直播录制出错\n{e} 发生错误的行数: {e.__traceback__.tb_lineno}")
                    warning_count += 1
        except Exception as e:
            logger.error(f"【错误信息】{e} 发生错误的行数: {e.__traceback__.tb_lineno}")
            warning_count += 1
        mon_time_remaining = mon_countdown - (time.time() - count_time)

        # 没播过/下播后没继播了 & 到点了，结束
        if rec_triggered is False and mon_time_remaining <= 0:
            break
        # 下播后没继播了，sleep到时间段过去，结束。如果需要下播后继续监测直到时间段过去，则删掉这个if块
        if interruption_prob is True and rec_triggered is False:
            mon_time_remaining = int(mon_time_remaining)
            if mon_time_remaining > 120:
                for i in range(mon_time_remaining // 120):
                    time.sleep(120)
            time.sleep(mon_time_remaining % 120 if mon_time_remaining > 0 else 0)
            break
        # if interruption_prob is True and rec_triggered is True:
        #     print('主播重新上线')
        tmp_mon_interval = mon_interval
        if warning_count > 10:
            tmp_mon_interval += 60
        # 应对暂时断播。录制结束60s后快速检测一下是否重新开播，若是，接着录。30s后如果还是关播状态，则使用mon_interval

        if rec_triggered is True and interruption_prob is False:
            # ffmpeg调用命令返回时间很大概率比实际播放结束时间晚3秒-2分钟，所以设置短点
            tmp_mon_interval = 30
            interruption_prob = True

        if loop_time:
            logger.info(
                f"【扫描】{author_name} 检测直播间循环等待 {tmp_mon_interval}秒")
        time.sleep(tmp_mon_interval)
    monitoring.discard(url_params[1])
    logger.info(f"【扫描】{author_name} 结束监控")


def check_ffmpeg_existence():
    dev_null = open(os.devnull, 'wb')
    try:
        subprocess.run(['ffmpeg', '--help'], stdout=dev_null, stderr=dev_null, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'【ffmpeg】测试调用ffmepg --help出错，检查环境配置。{e}')
        return False
    except FileNotFoundError:
        ffmpeg_file_check = subprocess.getoutput(ffmpeg_path)
        if ffmpeg_file_check.find("run") > -1 and os.path.isfile(ffmpeg_path):
            os.environ['PATH'] += os.pathsep + os.path.dirname(os.path.abspath(ffmpeg_path))
            return True
        else:
            logger.error("【ffmpeg】命令行监测不到ffmpeg，退出")
            sys.exit(0)
    finally:
        dev_null.close()
    return True


def read_config_value(config_parser: configparser.RawConfigParser, section: str, option: str, default_value: Any) \
        -> Union[str, int, bool]:
    try:
        config_parser.read(config_file, encoding=encoding)
        if '录制设置' not in config_parser.sections():
            config_parser.add_section('录制设置')
        if '推送配置' not in config_parser.sections():
            config_parser.add_section('推送配置')
        if 'Cookie' not in config_parser.sections():
            config_parser.add_section('Cookie')
        return config_parser.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        config_parser.set(section, option, str(default_value))
        with open(config_file, 'w', encoding=encoding) as f:
            config_parser.write(f)
        return default_value


# 应对换日，只能计算当天秒数来与24小时制时间比较
def _sec_since_midnight(ts=None) -> float:
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if ts:
        ts_list = re.split(r'[：:]', ts.strip().lstrip('0'))
        if len(ts_list) != 2 or '' in ts_list:
            return -1
        now = now.replace(hour=int(ts_list[0]), minute=int(ts_list[1]), second=0, microsecond=0)
        time.time()
    return (now - midnight).total_seconds()


def url_split(line: str):
    # url,author_name,W(eekday)/H(oliday),scan_interval(s),11:00-13:00,14:30-16:00,19:00-23:50
    line_list = re.split(r'[,，]', line)
    if len(line_list) < 5:
        logger.error(f'【URLconfig.ini】参数不足，跳过{line}')
        return None
    url = line_list[0]
    if ('http://' not in url) and ('https://' not in url):
        url = 'https://' + url
    author_name = line_list[1]
    dow_tag = str(line_list[2].lower().strip())
    if not line_list[3].isdigit():
        logger.error(f'【URLconfig.ini】扫描间隔不是数字，跳过{line}')
        return None
    interval = int(line_list[3])
    if dow_tag not in {'h', 'w'}:
        logger.error(f'【URLconfig.ini】HW参数错误，跳过{line}')
        return None
    ts_list = []
    for ts_span in line_list[4:]:
        ts_span = ts_span.split('-')
        if len(ts_span) != 2 or '' in ts_span:
            logger.error(f'【URLconfig.ini】{author_name}[{ts_span}]时间段格式错误，跳过')
            continue
        ts_start = _sec_since_midnight(ts_span[0])
        if ts_start < 0:
            logger.error(f'【URLconfig.ini】{author_name}[{ts_start}]时间格式错误，跳过')
            continue
        ts_end = _sec_since_midnight(ts_span[1])
        if ts_end < 0:
            logger.error(f'【URLconfig.ini】{author_name}[{ts_end}]时间格式错误，跳过')
            continue
        if ts_end <= ts_start:
            logger.error(f'【URLconfig.ini】{author_name}[{ts_start}-{ts_end}]时间end<start?，跳过')
            continue
        ts_list.append((ts_start, ts_end))
    if len(ts_list) == 0:
        logger.error(f'【URLconfig.ini】无法正常读到时间段，跳过。{line}')
        return None
    return url, author_name, dow_tag, interval, ts_list


def add_to_timeline(_dow_tag: str, _ts_key: tuple, _rec_par_val: list):
    if _dow_tag not in monitor_timeline_w_record_params:
        monitor_timeline_w_record_params[_dow_tag] = OrderedDict([(_ts_key, [_rec_par_val])])
    else:
        if _ts_key not in monitor_timeline_w_record_params[_dow_tag]:
            monitor_timeline_w_record_params[_dow_tag][_ts_key] = [_rec_par_val]
        else:
            monitor_timeline_w_record_params[_dow_tag][_ts_key].append(_rec_par_val)


def get_latest_modified_err_log():
    directory=os.path.split(os.path.realpath(sys.argv[0]))[0]+'/logs'
    files = os.listdir(directory)
    files.sort(key=lambda fn: os.path.getmtime(os.path.join(directory, fn)), reverse=True)
    for fn in files:
        if 'error' in fn:
            return os.path.join(directory, fn)


# --------------------------初始化程序-------------------------------------
logger.info("-----------------------------------------------------")
logger.info("|                   LiveRecorder                    |")
logger.info("-----------------------------------------------------")
# if not check_ffmpeg_existence():
#     logger.error("【ffmpeg】ffmpeg检查失败，程序将退出。")
#     sys.exit(1)
os.makedirs(os.path.dirname(config_file), exist_ok=True)
options = {"是": True, "否": False}
config = configparser.RawConfigParser()
# 校验两个config files
try:
    if not os.path.isfile(config_file):
        with open(config_file, 'w', encoding=encoding) as file:
            # 创建空ini
            pass
    ini_URL_content = ''
    if os.path.isfile(url_config_file):
        with open(url_config_file, 'r', encoding=encoding) as file:
            ini_URL_content = file.read().strip()
            if len(ini_URL_content) < 10:
                raise EOFError("URL_config.ini为空")
except OSError as err:
    logger.error(f"【config.ini/URLconfig.ini】读ini发生IO错误: {err}")
# 读取config.ini
video_save_path = read_config_value(config, '录制设置', '直播保存路径（不填则默认）', "")
folder_by_author = options.get(read_config_value(config, '录制设置', '保存文件夹是否以作者区分', "是"), False)
video_save_type = read_config_value(config, '录制设置', '视频保存格式ts|mp4|ts音频', "ts")
video_record_quality = read_config_value(config, '录制设置', '原画|超清|高清|标清|流畅', "原画")
if video_record_quality not in ["原画", "蓝光", "超清", "高清", "标清", "流畅"]:
    video_record_quality = '原画'
display_interval = int(read_config_value(config, '录制设置', '监控信息循环显示间隔(秒)', 60))
max_request = int(read_config_value(config, '录制设置', '同一时间访问网络的线程数', 3))
semaphore = threading.Semaphore(max_request)
loop_time = options.get(read_config_value(config, '录制设置', '是否显示循环秒数', "否"), False)
split_video_by_time = options.get(read_config_value(config, '录制设置', '分段录制是否开启', "否"), False)
split_time = str(read_config_value(config, '录制设置', '视频分段时间(秒)', 1800))
ts_to_mp4 = options.get(read_config_value(config, '录制设置', 'ts录制完成后自动转为mp4格式', "否"), False)
ts_to_mp3 = options.get(read_config_value(config, '录制设置', '音频录制完成后自动转为mp3格式', "否"), False)
delete_origin_file = options.get(read_config_value(config, '录制设置', '追加格式后删除原文件', "否"), False)
live_status_push = read_config_value(config, '推送配置', '直播状态通知(可选微信)', "")
xizhi_api_url = read_config_value(config, '推送配置', '微信推送接口链接', "")
begin_show_push = options.get(read_config_value(config, '推送配置', '开播推送开启（是/否）', "是"), True)
over_show_push = options.get(read_config_value(config, '推送配置', '关播推送开启（是/否）', "否"), False)
dy_cookie = read_config_value(config, 'Cookie', '抖音cookie(录制抖音必须要有)', '')
# ks_cookie = read_config_value(config, 'Cookie', '快手cookie', '')
weibo_cookie = read_config_value(config, 'Cookie', 'weibo_cookie', '')

if len(video_save_type) > 0:
    if video_save_type.upper().lower() == "MP4".lower():
        video_save_type = "MP4"
    elif video_save_type.upper().lower() == "TS音频".lower():
        video_save_type = "TS音频"
    else:
        video_save_type = "TS"
else:
    video_save_type = "TS"
# 主进程

with open(url_config_file, "r", encoding=encoding, errors='ignore') as file:
    for line in file:
        line = line.strip()
        if line.startswith("#") or len(line) < 20:
            continue
        url_param = url_split(line)
        if not url_param: continue
        url, author_name, dow_tag, mon_interval, scan_time_span = url_param

        url_host = url.split('?')[0].split('/')[2]
        platform_host = [
            'live.douyin.com',
            'v.douyin.com',
            'live.kuaishou.com',
            'weibo.com',
        ]
        if url_host in platform_host:
            if url_host == 'live.douyin.com':
                update_file(url_config_file, url, url.split('?')[0])
                url = url.split('?')[0]
            # dict{H:OrderedDict{(开始监控的时间，监控时长):[(video_quality,url,主播name, monitor_interval,mon_countdown),...]}
            #      W:OrderedDict{(开始监控的时间，监控时长):[(video_quality,url,主播name, monitor_interval,mon_countdown),...]}

            # “开始监控的时间”为从当日0点开始的秒数
            # 生成倒排
            for ts in scan_time_span:
                # 让监控线程到点结束
                mon_countdown = ts[1] - ts[0]
                add_to_timeline(_dow_tag=dow_tag, _ts_key=ts,
                                _rec_par_val=[video_record_quality, url, author_name, mon_interval, None])
        else:
            logger.error(f"【URLconfig.ini】{url} 未知链接.此条跳过")
            update_file(url_config_file, url, url, start_str='#')
# 按开始时间从小到大排序
for dow_tag in monitor_timeline_w_record_params:
    od = monitor_timeline_w_record_params[dow_tag]
    monitor_timeline_w_record_params[dow_tag] = OrderedDict(sorted(od.items(), key=lambda k: k[0][0]))

# 根据monitor_timeline_w_record_params跑无限循环并在对应的dow_tag、scan_time_span内、且不在monitoring中时开启monitor线程，
# 线程内外根据monitoring(key=url)、recording(key=(author_name,rec_start_time))两个变量通讯，前者让无限循环内不要开启重复线程，同时两者用来在display_info中报数

logger.info(f'读取的时间线是{monitor_timeline_w_record_params}')
# 显示信息切片、根据报错量更改同时扫描的直播间数量
threading.Thread(target=display_info, args=(display_interval,), daemon=True).start()
threading.Thread(target=change_max_connect, args=(), daemon=True).start()

datetime_today = date.today()
today_timeline = monitor_timeline_w_record_params[
    'h' if is_holiday(datetime_today) or not is_workday(datetime_today) else 'w']
e_fn=get_latest_modified_err_log()
err_lines=0
if e_fn:
    with open(e_fn, 'r',encoding='utf-8-sig',errors='ignore')as f:
        err_lines=len(f.readlines())
while True:
    # 跨日重读timeline
    if date.today() != datetime_today:
        datetime_today = date.today()
        today_timeline = monitor_timeline_w_record_params[
            'h' if is_holiday(datetime_today) or not is_workday(datetime_today) else 'w']
    for ts in today_timeline:
        if ts[0] <= _sec_since_midnight() <= ts[1]:
            url_param_list = today_timeline[ts]
            for url_param in url_param_list:
                if url_param[1] not in monitoring:
                    mon_countdown = ts[1] - _sec_since_midnight()
                    if mon_countdown < 60:
                        # 开始时距离最近时间段结束不足1分钟就不管了
                        continue
                    url_param[-1] = mon_countdown
                    t = threading.Thread(target=start_monitor_n_record, args=[url_param, monitoring],
                                         daemon=True)
                    t.start()
        time.sleep(2)
    time.sleep(60)
    # 如果error.log增多则推送报警
    e_fn = get_latest_modified_err_log()
    if e_fn:
        with open(e_fn, 'r',encoding='utf-8-sig',errors='ignore') as f:
            new_err_lines = len(f.readlines())
        if new_err_lines>err_lines:
            push_message(f'【liveRecorder】报错新增{new_err_lines-err_lines}条')
        elif new_err_lines<err_lines:
            push_message(f'【liveRecorder】报错新增{new_err_lines}条')
        err_lines=new_err_lines
