# liveRecorder
根据个人需求修改，基于https://github.com/ihmily/DouyinLiveRecorder。仅适合个人用途、少量低频监控、小服务器部署(1c2g)。

重整代码，去除个人不需要的功能，仅保留支持douyin kuaishou weibo。使用时间线串联监控扫描顺序，每个直播间指定独立的监测时间段和扫描循环间隔(见config/URL_config.ini注释)。

感谢 https://github.com/ihmily/DouyinLiveRecorder (@ihmily)提供基础框架

感谢 https://github.com/ihmily/DouyinLiveRecorder/issues/86 (@18202821297)指出ks的模拟方式


逻辑注释见main.py

整体架构同ihmily,填完两个.ini后nohup python3 main.py即可。依赖pip3 install loguru chinese_calendar drissionpage，以及本地安装chrome（sudo apt install google-chrome）

个人关于ks的风控测试经验：

1、使用风控模型，检测到非人类操作行为即封ip，但可通过人类行为解封。但交替频率高可能提升监控关注等级。

2、风控与cookie无关，与访问频率关系小。1小时扫一次和1秒扫一次都可能被封。

3、提升监控关注等级 可能包括更频繁的、连续多次、不同类型的验证码，更频繁的“访问过快”。

4、使用过免/付费代理池，效果极差，不建议尝试。（脏ip+网络差+成本高）

快手滑块.py可过（感谢 https://hyb.life/ 提供滑块缺口识别），但暂未实际用上(真被盯上其实自动化应对很麻烦，不如调整访问方式以及x11连上去手动解决下)。
