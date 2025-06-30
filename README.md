# liveRecorder
根据个人需求修改，基于https://github.com/ihmily/DouyinLiveRecorder。仅适合个人用途、少量低频监控、小服务器部署。

*250630
暂时能录快手的麻烦办法：
快手自25年不登陆100%弹“请求过快”或验证码，这两种状态都无法拿到直播地址；登录后也有概率弹验证码。

由于没有充分研究但简单传cookie无法维持登录状态，索性直接使用chrome的用户数据机制维持一致性，就像本地打开网站不用每次都登陆。

这里使用mobaXterm客户端打开图形界面手工配置，chrome://version找到用户数据文件夹并复制一份（见spider.py line 303）,
使用google-chrome --user-data-dir="复制到的路径"加载该用户数据，打开快手登录。（chrome安全机制貌似阻止直接使用默认的而非复制品）

此外加了过滑块验证码，文字、旋转等目前没发现也暂无办法。

话说这公司一年风控策略就改了3次，天天和用户斗智斗勇，没啥经济利益的也就没人愿意更新吧。

*240816 
输出全部整理在info.log/error.log，1am~10am不输出info。增加报错微信通知。

目前以330s一次扫描频率已运行一周无误。快手如涉及多url扫描建议修改为在一个thread中完成，避免频繁访问。但目前已满足本人需求。

感谢 https://github.com/ihmily/DouyinLiveRecorder (@ihmily)提供基础框架

重整代码，去除个人不需要的功能，仅保留支持douyin kuaishou weibo。使用时间线串联监控扫描顺序，每个直播间指定独立的监测时间段和扫描循环间隔(见config/URL_config.ini注释)。

感谢 https://github.com/ihmily/DouyinLiveRecorder/issues/86 (@18202821297)指出ks的模拟方式


逻辑注释见main.py

整体架构同ihmily,填完两个.ini后nohup python3 main.py即可。依赖pip3 install loguru chinese_calendar drissionpage

ubuntu chrome安装：（用apt 会卡在snap）

`wget "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" -O chrome.deb`

`sudo dpkg -i chrome.deb`

个人关于ks的风控测试经验：

1、使用风控模型，检测到非人类操作行为即封ip，但可通过人类行为解封。但交替频率高可能提升监控关注等级。

2、风控与cookie无关，与访问频率关系小。1小时扫一次和1秒扫一次都可能被封。

3、提升监控关注等级 可能包括更频繁的、连续多次、不同类型的验证码，更频繁的“访问过快”。

4、使用过免/付费代理池，效果极差，不建议尝试。（脏ip+网络差+成本高）

快手滑块.py各处拼凑修改得来，可较高概率过滑块验证，但本工程未用上。
