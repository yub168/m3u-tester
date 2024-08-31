import m3utester as test
import json
from m3utester import Item
import pandas as pd



def creatIptvTestList(sourcelist=None,startNum=None,endNum=None,codeTo4Str=None):
    '''
      ### params
        sourcelist : 要检测的 地址列表 类型为 ：{ key:value }
        startNum : 编码开始位置
        endNum:    编码结束位置
        codeTo4Str: 频道编码方式
              1 ：默认值 频道编码为4位字符中 ‘0012’
              0 ：频道编码为数字字符 ‘12’
    '''
    iptvTestResult='iptvTestResult.json'
    startNum = startNum if startNum else 1
    endNum = endNum if endNum else 200
    codeTo4Str = codeTo4Str if codeTo4Str else 1
    if not sourcelist:
      sourcelist={
          '101.229.227.246:7777':'http://101.229.227.246:7777/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0',#速度有点卡 300-600K
          '111.160.17.2:59902':'http://111.160.17.2:59902/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0',# 速度一般 300-500k 但台少 只有卫视且还少部分台 央卫视编码同上
          '113.57.93.165:9900':'http://113.57.93.165:9900/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 速度不好300K，且台少 央卫视编码同上 放弃
          '119.163.199.98:9901':'http://119.163.199.98:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 速度差200-300k 只有央卫视 央卫视编码同上 放弃
          '123.189.36.186:9901':'http://123.189.36.186:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 速度较好500-800 多辽宁省台
          '223.151.49.74:59901':'http://223.151.49.74:59901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0',# 速度较好600-1000以上且稳定 卫视台少，多湖南省台
          '223.159.8.218:8099':'http://223.159.8.218:8099/tsfile/live/{}_1.m3u8?key=txiptv&playlive=0&authid=0', #速度较好400-800 卫视台少，多湖南省台
          '58.48.37.158:1111':'http://58.48.37.158:1111/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # # 速度较好500-800 但播放时有卡顿很不稳定 放弃
          '58.51.111.46:1111':'http://58.51.111.46:1111/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 速度较好500-800 播放畅 有部分湖北省台
          '60.208.104.234:352':'http://60.208.104.234:352/tsfile/live/{}_1.m3u8?key=txiptv&playlive=0&authid=0', # 速度较好500-800 播放顺 只有央卫视
          '58.245.97.28:9901':'http://58.245.97.28:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=0&authid=0', #速度好1000以上且稳定 播放顺 有小量吉林省台
          '58.220.219.14:9901':'http://58.220.219.14:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', #速度差 100-300k 播放卡 只有央卫视
          '223.241.247.214:85':'http://223.241.247.214:85/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', #速度较好400-800 播放顺
          #'222.134.245.16:9901':'http://222.134.245.16:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=', # 没有结果
          '202.100.46.58:9901':'http://202.100.46.58:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', #速度好1000以上且稳定 卫视播放稍有卡
          #'125.107.96.172:9901':'http://125.107.96.172:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 没有结果
          '111.9.163.109:9901':'http://111.9.163.109:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', #速度一般 300-500k  台很少 放弃
          '110.189.102.15:9901':'http://110.189.102.15:9901/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', #速度较快 1000K以上 有少量四川省台
          
          #'111.225.112.74:808':'http://111.225.112.74:808/tsfile/live/{}_1.m3u8?key=txiptv&playlive=1&authid=0', # 没有结果
          #'1.180.2.93:9901':'http://1.180.2.93:9901/tsfile/live/{}_1.m3u8',
          '123.166.61.70:8003':'http://123.166.61.70:8003/hls/{}/index.m3u8', # 速度变化大 300-2000k 大部分在500K
          '101.27.36.164:2888':'http://101.27.36.164:2888/hls/{}/index.m3u8', # 速度差 200-300K
          '112.123.206.32:808':'http://112.123.206.32:808/hls/{}/index.m3u8', #速度较好 600-1000k 画面不正常
          '175.31.21.146:4480':'http://175.31.21.146:4480/hls/{}/index.m3u8', #速度差 100-300k 
          '42.48.17.204:808':'http://42.48.17.204:808/hls/{}/index.m3u8', #速度较好 300-1000K 波动大 平均600
          '61.138.54.155:2233':'http://61.138.54.155:2233/hls/{}/index.m3u8', #速度一般 300-500k 
          '219.147.200.9:18080':'http://219.147.200.9:18080/newlive/live/hls/{}/live.m3u8' #速度差 100-300k 
         
          # 地址 范围太宽
          # http://124.205.11.239:91/live/SDWShd-8M/live.m3u8$饭太硬_TV 山东卫视
          # http://124.205.11.239:91/live/SZWShd-8M/live.m3u8$饭太硬_TV 深圳卫视
         
          # http://221.0.78.198:1681/hls/10234/index.m3u8$饭太硬_TV 江苏卫视
          # http://106.124.91.222:9901/tsfile/live/21212_1.m3u8$饭太硬_TV 新疆卫视
          
          }

    oldList=[]
    finishGroups=[]
    with open(iptvTestResult, 'r', encoding='utf-8') as f:
        oldList=json.load(f)
        if oldList:
          finishGroups=pd.DataFrame(oldList)['groups'].to_list()
    dicts={}
    # 生成测试列表 并测试 返回测试结果并添加到 test1result.json 文件中
    for key,value in sourcelist.items():
        if key not in finishGroups:
          groups=key
          channels={}
          for i in range(startNum,endNum):
              if codeTo4Str:
                 code=format(i,'04d')
              else:
                 code=str(i)
              channels[str(i)]=value.format(code)
          dicts[groups]=channels
        else:
            print(f'{key} 已经测试过！！！')
    return dicts

def creatTestItems(group,dicts):
    '''
    dicts= 
          {
            channel1:url,
            channel2:url
          }
    '''
    items=[]
    if dicts:
         for channel,url in dicts.items() :
            item=Item()
            item.groups=group
            item.title=channel
            item.url=url
            item.source=group
            items.append(item)
    return items

def autoipTvTest(sourcelist=None,startNum=None,endNum=None,codeTo4Str=None,minSpeed=None,minHeight=None,testTime=None):
  dicts=creatIptvTestList(sourcelist,startNum=startNum,endNum=endNum,codeTo4Str=codeTo4Str)
  
  for group,channels in dicts.items():
    test.writeTestInfo(f'============开始测试 :{group}==================',0)
    items=creatTestItems(group,channels)
    results=test.start(items,minSpeed,minHeight,testTime)
    if results:
      results=test.translateTilte(results)
      test.addTolivePool(results,'iptvTestResult.json')
    test.writeTestInfo(f'============{group} 测试完成,共获取 {len(results)} 个地址==================')
  test.creatLiveConfig('iptvTestResult.json','iptvConfig.txt')
if __name__ == '__main__':
  autoipTvTest(minSpeed=100,testTime=10)
  # with open('iptvTestResult.json','r',encoding='utf-8') as f :
  #    data=json.load(f)
  #    data=test.translateTilte(data)
  #    print(data)