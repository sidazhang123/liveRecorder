# ks很蛋疼，似乎对incognito很不友好，每次打开必出验证码（当然一般不影响html的streamurl读取）。所以不建议在生产环境高频反复尝试。
# 也不知道是不是我的ip测试多了，出现过以下奇葩情况
# 1、可以进live.kuaishou.com，但访问具体直播间（不管在不在播）页面只显示“访问过快”无法看直播，甚至随机刷都可能出现
# 2、验证码滑块一次过，然后又出旋转验证码、汉字验证码
# 以上情况挂代理、重启浏览器短期无法缓解
from DrissionPage import ChromiumPage, ChromiumOptions
import time,cv2,random
import numpy as np
def identify_gap(bg, cut,bg_disp_width):
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
    for i in [coor[0]*bg_disp_width/bg_actual_width for coor in top_locs]:
        if i >150:
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
bg='bg-img.png'
slider='slider-img.png'

co = ChromiumOptions()
co.set_argument('--disable-gpu')
co.set_argument("--disable-blink-features=AutomationControlled")
co.set_user_agent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36')
co.set_argument('--charset=UTF-8')  # 设置编码为 UTF-8
co.incognito(True)
page = ChromiumPage(addr_or_opts=co)
# 模拟正常进入直播间。目前浅测一天刷个几十次用这招是够的，其实不需要验证码/代理池
# (代理试都别试，付费的一样不行，池子都脏了。直接requests一两次就封，模拟的话网速连页面元素都加载不完。除非你花大钱买企业级)
# page.get('https://live.kuaishou.com')
# player_container = page.ele('@class=kwai-player-container-video')
# page.actions.move_to(player_container.rect.midpoint)
# time.sleep(1)
# page.actions.move_to('进入直播间').click()
# 滚轮刷俩视频
# for _ in range(3):
#     page.actions.scroll(1)
#     time.sleep(1)
# time.sleep(1)
page.get('https://live.kuaishou.com/u/G81210582')
time.sleep(10)
if '<iframe' in page.html:
    iframe = page.get_frame(1)
    container=iframe('@class:image-container')
    slider_btn = iframe('@class=slider-btn')
    disp_width=float(container.style('width').replace('px','').strip())
    iframe('@class=bg-img').save(name=bg,rename=False)
    slider_ele=iframe('@class=slider-img')
    slide_offset=float(slider_ele.style('left').replace('px','').strip())
    slider_ele.save(name=slider,rename=False)
    print(disp_width,slide_offset)
    distance=round(identify_gap(bg, slider,disp_width) - slide_offset)
    track=get_tracks_2(distance,1,ease_out_quad)
    print(f'在页面上x轴实际要拖动：{distance}')
    print('track',track)
    page.actions.hold(slider_btn)
    for t in track:
        page.actions.move(t,random.randint(-5, 5))
        time.sleep(0.01)
    page.listen.start('kSecretApiVerify')
    page.actions.release()
    captcha_rsp = page.listen.wait()
    captcha_res=captcha_rsp.response.body
    if captcha_res['desc']=='ok':
        #成功
        pass
    print(captcha_res)
    page.listen.stop()
    # 阻塞用
    while True:
        time.sleep(60)

page.close()
page.quit()
