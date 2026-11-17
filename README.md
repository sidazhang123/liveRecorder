# liveRecorder

一个基于 [ihmily/DouyinLiveRecorder](https://github.com/ihmily/DouyinLiveRecorder) 修改的直播监控录制工具，支持抖音、快手、微博三个平台，可对指定直播间按时间线自动扫描开播状态，并在开播后调用 ffmpeg 自动录制。

仅适合个人用途、少量低频监控、小服务器部署。

## 功能特性

- 多平台支持：抖音（`live.douyin.com`）、快手（`live.kuaishou.com`）、微博（`weibo.com`）。
- 时间线调度：每个直播间可配置独立的监控时间段与扫描间隔，并区分工作日（`w`）与周末/法定假日（`h`）。
- 自动录制：检测到开播后自动调用 ffmpeg 录制，支持分段录制。
- 多种保存格式：`ts` / `mp4` / `ts音频` / `mp3`，录制完成后可选自动转码（`ts` 转 `mp4`、音频转 `mp3`）。
- 清晰度选择：原画 / 蓝光 / 超清 / 高清 / 标清 / 流畅。
- 开关播推送：通过微信（息知 `xizhi` 接口）推送开播、关播通知。
- 报错推送：`error.log` 新增错误时自动推送报警内容。
- 日志输出：`logs/info.log` 与 `logs/error.log`，每日 1:00~10:00 不输出 info 日志。
- 快手滑块验证码处理：使用 DrissionPage 加载 Chrome 用户数据维持登录态，结合 OpenCV 识别并滑动滑块。

## 支持平台

| 平台 | 直播间 URL 示例（电脑端地址） |
| --- | --- |
| 抖音 | `https://live.douyin.com/32xxxxxx692` |
| 快手 | `https://live.kuaishou.com/u/32xxxxxx692` |
| 微博 | `https://weibo.com/u/13xxxxxxx1` |

## 技术栈 / 依赖

- Python 3
- [ffmpeg](https://ffmpeg.org/)：录制核心，需保证 `ffmpeg` 命令在 PATH 中可用
- Google Chrome：快手平台使用 DrissionPage 无头浏览器访问页面
- Python 第三方库：`loguru`、`chinese_calendar`、`DrissionPage`、`requests`、`numpy`、`opencv-python`

安装 Python 依赖：

```bash
pip3 install loguru chinese_calendar drissionpage requests numpy opencv-python
```

## 目录结构

```
liveRecorder/
├── main.py               # 主程序：时间线调度、监控线程、ffmpeg 录制
├── spider.py             # 各平台直播流地址获取、快手滑块验证码处理
├── web_rid.py            # 抖音房间 ID / sec_user_id 解析
├── msg_push.py           # 微信（息知）推送
├── utils.py              # 异常追踪装饰器
├── logger.py             # loguru 日志配置
├── 快手滑块.py            # 独立的快手滑块验证码脚本（主程序未使用）
├── restart_recorder.sh   # 停止并重启录制进程的脚本
└── config/
    ├── config.ini        # 主配置：录制 / 推送 / Cookie
    ├── URL_config.ini    # 直播间监控列表
    └── weibo_cookie.txt  # 微博 Cookie（每行一个，可配置多个）
```

## 安装与环境要求

1. 安装 Python 3 与 ffmpeg，确保 `ffmpeg` 命令可直接调用。
2. 安装 Google Chrome（快手平台需要）。Ubuntu 下可这样安装：

   ```bash
   wget "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" -O chrome.deb
   sudo dpkg -i chrome.deb
   ```

3. 安装 Python 依赖（见上文）。
4. 克隆仓库并进入目录：

   ```bash
   git clone https://github.com/sidazhang123/liveRecorder.git
   cd liveRecorder
   ```

## 使用方法

1. 编辑 `config/URL_config.ini`，填写要监控的直播间列表（格式见下文）。
2. 编辑 `config/config.ini`，配置录制参数、推送接口与抖音 Cookie。
3. 如需录制微博，将微博 Cookie 写入 `config/weibo_cookie.txt`（每行一个）。
4. 启动程序：

   ```bash
   python3 main.py
   ```

   后台运行可用：

   ```bash
   nohup python3 main.py > /dev/null 2>&1 &
   ```

   也可使用 `restart_recorder.sh` 停止并重启录制进程（注意：该脚本中的 Python 脚本路径 `PYTHON_SCRIPT` 与 `nohup /usr/bin/python3` 为作者服务器上的硬编码路径，使用前需按实际环境修改）。

## 配置说明

### config/URL_config.ini（直播间监控列表）

以 `#` 开头的行为注释。每个直播间一行，参数以英文逗号分割，依次为：

```
url,主播名,假日/工作日,监控扫描间隔(秒),扫描时间段
```

- `url`：直播间电脑端地址。
- `主播名`：自定义名称，用于扫描去重与开关播推送展示。
- `假日/工作日`：`h` 表示周末/法定假日（holiday），`w` 表示工作日（workday）。
- `监控扫描间隔(秒)`：本条直播间的扫描循环间隔。
- `扫描时间段`：当天内的所有扫描时间段，格式为 `HH:MM-HH:MM`，可写多个并用逗号分隔，顺序不限。

示例：

```
https://live.douyin.com/32xxxxxx692,主播名1,w,100,12:00-14:00,19:00-22:20
https://live.douyin.com/32xxxxxx692,主播名1,h,100,12:00-14:00,19:00-22:20

https://live.kuaishou.com/u/32xxxxxx692,主播名2,h,100,12:00-14:00

https://weibo.com/u/13xxxxxxx1,主播名3,h,600,10:00-14:30,16:00-17:00,19:00-23:59
```

某直播间想每天都扫，可分别写 `w`、`h` 各一行。

### config/config.ini（主配置）

`[录制设置]`

| 配置项 | 说明 |
| --- | --- |
| `直播保存路径（不填则默认）` | 录像保存目录，留空则保存到脚本目录下的 `downloads/` |
| `保存文件夹是否以作者区分` | `是` / `否`，是否按主播名建立子目录 |
| `视频保存格式ts\|mp4\|ts音频\|mp3` | 保存格式，取其一 |
| `原画\|超清\|高清\|标清\|流畅` | 录制清晰度，取其一 |
| `同一时间访问网络的线程数` | 同时访问网络的并发线程数 |
| `是否显示循环秒数` | `是` / `否`，是否在日志中显示循环等待秒数 |
| `分段录制是否开启` | `是` / `否` |
| `视频分段时间(秒)` | 分段录制时的每段时长 |
| `ts录制完成后自动转为mp4格式` | `是` / `否` |
| `音频录制完成后自动转为mp3格式` | `是` / `否` |
| `追加格式后删除原文件` | `是` / `否` |
| `监控信息循环显示间隔(秒)` | 监控信息在日志中的显示间隔 |

`[推送配置]`

| 配置项 | 说明 |
| --- | --- |
| `直播状态通知(可选微信)` | 填写 `微信` 开启推送 |
| `微信推送接口链接` | 息知（xizhi）推送接口链接 |
| `开播推送开启（是/否）` | `是` / `否` |
| `关播推送开启（是/否）` | `是` / `否` |

`[Cookie]`

| 配置项 | 说明 |
| --- | --- |
| `抖音cookie(录制抖音必须要有)` | 录制抖音必须填写有效的抖音 Cookie |

### config/weibo_cookie.txt（微博 Cookie）

每行存放一个微博 Cookie，可配置多个。程序会依次尝试，失效的 Cookie 会被自动从文件中删除；若全部失效会报错。

## 输出 / 结果说明

- 录像文件默认保存在脚本目录下的 `downloads/`，按平台（`抖音直播` / `快手直播` / `微博直播`）建立子目录；若开启“按作者区分”，再按主播名建立子目录。文件名为 `主播名_时间戳.后缀`（分段录制时为 `主播名_时间戳_序号.后缀`）。
- 运行日志写入 `logs/info.log` 与 `logs/error.log`，带 7 天保留、按大小滚动；info 日志每日 1:00~10:00 不输出。

## 注意事项 / 已知限制

- 本工具仅适合个人用途、少量低频监控、小服务器部署。
- 快手自 2025 年起不登录几乎必然出现“请求过快”或验证码，因此快手录制依赖 Chrome 用户数据维持登录态。需先复制一份 Chrome 用户数据目录，用 `google-chrome --user-data-dir="复制到的路径"` 打开并登录快手，然后在 `spider.py` 中通过 `co.set_user_data_path('kwai_user_profile')` 指定该目录（见 `spider.py` 中 `get_kuaishou_stream_url`）。
- 快手验证码目前只能处理滑块类型，文字、旋转等验证码暂未支持。
- 录制抖音必须提供有效的抖音 Cookie。
- `check_ffmpeg_existence()` 检查在主程序中默认被注释，因此请自行确保 `ffmpeg` 在 PATH 中可用。
- `restart_recorder.sh` 内含作者服务器的硬编码路径，使用前需修改。
