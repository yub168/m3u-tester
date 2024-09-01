# m3u-tester
此脚本主要用来测试m3u视频资源的连接速度，每个人的网络环境不同，测试结果也会不一样

此脚本基于python 3.8.2编写，其他版本并未测试，本人也不是很熟悉python，有写的不好的地方，欢迎指正
# 使用
脚本会检查当前目录下的`.m3u`文件，并测试所有检测到的视频流资源的网络连接速度
```
python3 m3u-tester.py
```
每个连接测试大约需要5秒左右的时间，如果资源较多，可能需要花费较长时间才能完成

测试完成后，会在当前目录生成以下文件：
1. result.json，所有测试的结果，包括extinf，url，speed
2. useful.m3u，速度大于200KB/sec
3. good.m3u，速度大于500KB/sec
4. wonderful.m3u，速度大于700KB/sec
5. excellent.m3u，速度大于1MB/sec

# 地址源
1. https://iptv.b2og.com/cymz6_lives.m3u 速度不错

# china IPTV
http://223.151.49.74:59901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0$饭太硬_TV
http://223.151.49.74:59901/tsfile/live/0018_1.m3u8?key=txiptv&playlive=1&authid=0$俊佬线路_直播 CCTV-5+ 体育赛事,
http://223.151.49.74:59901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0$俊佬线路_直播 CCTV-13 新闻

http://223.159.8.218:8099/tsfile/live/0001_1.m3u8?key=txiptv&playlive=0&authid=0摸鱼儿_SAO0
http://223.159.8.218:8099/tsfile/live/0013_1.m3u8?key=txiptv&playlive=0&authid=0$摸鱼儿_SAO0 CCTV-13 新闻,
http://223.159.8.218:8099/tsfile/live/0122_1.m3u8?key=txiptv&playlive=0&authid=0$摸鱼儿_SAO0 北京卫视,

http://113.57.93.165:9900/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0晨瑞_公众号【晨瑞黑科】直播源

http://101.229.227.246:7777/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0$摸鱼儿_SAO0

http://58.245.97.28:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=0&authid=0$摸鱼儿_SAO0

http://58.51.111.46:1111/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0晨瑞_公众号【晨瑞黑科】直播源
http://58.51.111.46:1111/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0$晨瑞_公众号【晨瑞黑科】直播源  cctv5+
http://58.51.111.46:1111/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0$晨瑞_公众号【晨瑞黑科】直播源 CCTV-6 电影
http://58.51.111.46:1111/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0$晨瑞_公众号【晨瑞黑科】直播源 CCTV-13 新闻

http://58.48.37.158:1111/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0$晨瑞_公众号【晨瑞黑科】直播源 CCTV-13 新闻

http://60.208.104.234:352/tsfile/live/0007_1.m3u8?key=txiptv&playlive=0&authid=0$饭太硬_TV CCTV-7 国防军事
http://60.208.104.234:352/tsfile/live/0013_1.m3u8?key=txiptv&playlive=0&authid=0$饭太硬_TV CCTV-13 新闻,


http://218.76.32.193:9901/tsfile/live/1020_1.m3u8$饭太硬_TV CHC动作电影
http://218.76.32.193:9901/tsfile/live/1018_1.m3u8$饭太硬_TV CHC家庭影院

http://119.163.199.98:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0$摸鱼儿_SAO0 北京卫视

#####
http://mobilelive-ds.ysp.cctv.cn/ysp/2013693901.m3u8?key=txiptv&playlive=1&authid=0$饭太硬_TV  CCTV-6 电影,