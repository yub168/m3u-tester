#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: chaichunyang@outlook.com
import os
import json
import time
from urllib.request import urlopen,Request
import requests
from func_timeout import func_set_timeout
from ffmpy import FFprobe
from subprocess import PIPE
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import subprocess
pd.set_option('display.unicode.ambiguous_as_wide', True)

#pd.set_option('display.unicode.east_asian_width', True)
#pd.set_option('display.unicode.east_asian_width', True)

class Item:
    def __init__(self):
        self.extinf = ''
        self.title = ''
        self.groups = ''
        self.url = ''
        self.speed = -1
        self.width = 0
        self.height = 0
        self.source=''

    def __json__(self):
        return {'extinf': self.extinf, 'url': self.url, 
                'groups':self.groups,'title':self.title,
                'speed': self.speed,'width':self.width,
                'height':self.height}


class ItemJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)


class Downloader:
    def __init__(self, url):
        self.url = url
        self.startTime = time.time()
        self.recive = 0
        self.endTime = None
        self.videoInfo=None
        self.testTime=0
        
    def getSpeed(self):
        if self.endTime and self.recive != -1:
            return self.recive / (self.endTime - self.startTime)//1000
        else:
            return -1

class Setting:
    def __init__(self):
        with open('setting.json','r',encoding='utf-8') as f :
            self.setting=json.load(f)
    # def openFile(self):
    #     with open('setting.json','r',encoding='utf-8') as f :
    #         setting=json.load(f)
    #         return setting
    def getDownloadMinSpeed(self):
        return self.setting.get('minDownloadSpeed')
    
    def getVideoMinHeight(self):
        return self.setting.get('minVideoHeight')
    
    def getGroupsFilter(self):
        return self.setting.get('groupsFilter')
    
    def getSourceUrls(self):
        return self.setting.get('sourceUrls')
    
    def getSourceBlack(self):
        return self.setting.get('sourceBlack')
    
    def addSourceBlack(self,item):
        self.setting.get('sourceBlack').update(item)
        with open('setting.json','w',encoding='utf-8') as f :
            json.dump(self.setting,f,ensure_ascii=False)

    def getHeaders(self):
        return self.setting.get('headers')
    
    def getLivesCount(self):
        return self.setting.get('livesCount')
    def getLivesModel(self):
        return self.setting.get('livesModel')
    
def addtestRecord(item):
    testRecords=[]
    with open('testRecords.json','r',encoding="utf-8") as f:
        testRecords=json.load(f)
        testRecords.append(item)
    with open('testRecords.json','w',encoding="utf-8") as f:
        json.dump(testRecords,f,ensure_ascii=False)

def writeTestInfo(content,hasBlank=1):
    with open('testInfo.txt', 'a', encoding='utf-8') as f:
        print(content,file=f)
        if hasBlank:
            print('',file=f)

# 判断列表中的值是否包含在指定的字符串中
def isIn(list,str):
    for word in list:
        if word in str:
            return True
    return False

# 根据配置地址生成待检测列表     
def getAllM3UItems(dir,name):
    items = []
    if dir.startswith('http'):
        resp=requests.get(dir,headers=Setting().getHeaders())
        if resp.status_code==200:
            resp.encoding='utf-8'
            if '#EXTM3U' in resp.text:
                items=readM3u(resp,name)
            if '#genre#' in resp.text:
                items=readText(resp,name)
        else:
            print('downLoad error!!!')
    else:
        print('not net address!!!')
    return items

# 读取 Txt 配置文件生成待测试列表
def readText(resp,name):
    items=[]
    groups = ''
    groupsFilter=Setting().getGroupsFilter()
    for line in resp.text.splitlines():
        if '#genre#' in line :
            groups=line.split(',')[0]
        elif  line and isIn(groupsFilter,groups):
            #print('符合分组：',groups)
            item=Item()
            info=line.split(',')
            if len(info)>1:
              title=line.split(',')[0]
              urlStr=line.split(',')[1]
              if urlStr:
                  url=urlStr.split('$')[0]
                  item.source=name
                  item.groups=groups
                  item.title=title
                  item.url=url
                  items.append(item)
            else:
                print('split error : '+line)
    return items
      
# 读取 m3u 配置文件生成待测试列表               
def readM3u(resp,name):
    items=[]
    extinf = ''
    groups=''
    groupsFilter=Setting().getGroupsFilter()
    title=''
    for line in resp.text.splitlines():
        if line.startswith('#EXTM3U'):
            continue
        if extinf :
            #print('当前分组：',groups)
            if isIn(groupsFilter,groups):
              item=Item()
              item.extinf=extinf
              item.groups=groups
              item.title=title
              url=line.split('$')[0]
              item.source=name
              item.url=url
              items.append(item)
            extinf = ''
        if line.startswith('#EXTINF'):
            extinf = line 
            title=extinf.split(',')[1]
            groupStr=extinf.split(',')[0]
            pattern='group-title=\"(.*?)\"'
            if re.search(pattern,groupStr):
              groups=re.search(pattern,groupStr).group(1)
            #print(groups+' : '+title)

            ## 以下部分用于生成lives空列表
    #         creatLives(lives,groups,title)
            
    # try:
    #     # 包含测试结果，存入json
    #     with open('liveTest2.json', 'w+', encoding="utf-8") as f:
    #         json.dump(lives, f,ensure_ascii=False)
    # except BaseException as e:
    #     print('保存json失败 %s' % e)
    return items       

# 用于自动生成空的 lives.json 表
def creatLives(lives,groups,title):
    if groups in lives:
        lives[groups][title]=[]
    else:
        lives[groups]={}
        lives[groups][title]=[]
        
# 获取m3u8地址中的真实视频地址用于测试    
def getStreamUrl(m3u8):
    urls = []
    try:
        prefix = m3u8[0:m3u8.rindex('/') + 1]
        request = Request(m3u8,headers=Setting().getHeaders())
        with urlopen(request, timeout=2) as resp:
            top = False
            second = False
            firstLine = False
            for line in resp:
                line = line.decode('utf-8')
                line = line.strip()
                # 不是M3U文件，默认当做资源流
                if firstLine and not '#EXTM3U' == line:
                    urls.append(m3u8)
                    firstLine = False
                    break
                if top:
                    # 递归
                    if not line.lower().startswith('http'):
                        line = prefix + line
                    urls += getStreamUrl(line)
                    top = False
                if second:
                    # 资源流
                    if not line.lower().startswith('http'):
                        line = prefix + line
                    urls.append(line)
                    second = False
                if line.startswith('#EXT-X-STREAM-INF:'):
                    top = True
                if line.startswith('#EXTINF:'):
                    second = True
            resp.close()
    except BaseException as e:
        print('get stream url failed! %s' % e)
    return urls

# 根据下载测试的视频字节流分析视频信息
@func_set_timeout(18)
def get_video_info(content):
    
    videoInfo={}
    startTime=time.time()
    #print(f"==============start ffprobe time : {time.time()}============")
    try:

      # 参数 ‘-’ 是不设置 ffprobe 以stdin做为输入
      command = ['ffprobe','-', '-v', 'quiet', '-print_format', 'json',  '-show_streams']
      # 参数 input 与 stdin=subprocess.PIPE 二选一 text=False 设置输入为非字符
      process = subprocess.run(command,timeout=18,stdout=subprocess.PIPE,stderr=subprocess.PIPE,input=content)

      # 用 Popen 方式
      # process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=False)
      # # 通过 stdin 发送字节数据
      # process.stdin.write(url)
      # process.stdin.close()  # 关闭 stdin，让 ffprobe 开始处理数据
      # # 读取 stdout 和 stderr
      # stdout, stderr = process.communicate()

      if process.returncode==0:
          cdata=json.loads(process.stdout.decode('utf-8'))
          if cdata:
              vwidth = 0
              vheight = 0
              for i in cdata['streams']:
                  if i['codec_type'] == 'video':
                      if vwidth <= i['coded_width']:  # 取最高分辨率
                          vwidth = i['coded_width']
                          vheight = i['coded_height']
              videoInfo["height"]=vheight
              videoInfo["width"]=vwidth
      else:
          print("Error: ffprobe failed to execute. Return code: {}".format(process.stderr.decode('utf-8')))  
      #print(f"==============stop ffprobe time : {time.time()}=============")  
      return videoInfo,time.time()-startTime
    except Exception as e:
        # traceback.print_exc()
        print('ffprobe get videoInfo error:',e)
        return False

# 下载测试
def downloadTester(downloader: Downloader,minSpeed=Setting().getDownloadMinSpeed()):
   
    try:
        resp=requests.get(downloader.url,stream=True,timeout=2,headers=Setting().getHeaders())
        content=bytes()
        for chunk in resp.iter_content(chunk_size=10240):
            if not chunk or (time.time()-downloader.startTime)>5:
                break
            content=content+chunk
            downloader.recive = downloader.recive + len(chunk)
        downloader.endTime = time.time()
        downloader.testTime=downloader.endTime-downloader.startTime
        if downloader.getSpeed()>minSpeed:
          videoInfo,testTime=get_video_info(content)
          downloader.testTime=downloader.testTime+testTime
          if videoInfo:
              downloader.videoInfo=videoInfo
        resp.close()
    except BaseException as e:
        print("downloadTester got an error %s" % e)
        downloader.recive = -1
    #os.remove(filename)

# 开始检测单一地址可用数量 
def start(items,minSpeed=None,minHeight=None):
    
    filterItem=[]
    print(f'共 {len(items)} 项需要检测！')
    if len(items):
      # 循环测速 加入多线程
      with ThreadPoolExecutor(max_workers=6) as executor:
        filterItem=list(executor.map(test,items,len(items)*[minSpeed],len(items)*[minHeight]))
        filterItem=[result for result in filterItem if result is not None]
    return filterItem,len(items)

finishedUrls=set()
# 测试项目
def test(item,minSpeed=None,minHeight=None):
    # print('params speed :',minSpeed)
    # print('params height:',minHeight)
    name=item.source
    print(f'测试：源：{name} {item.groups}__{item.title}')
    if not minHeight:
        minHeight=Setting().getVideoMinHeight()
    if not minSpeed:
        minSpeed=Setting().getDownloadMinSpeed()
    url = item.url
    if url not in finishedUrls:
      finishedUrls.add(url)
      stream_urls = []
      if url.lower().endswith('.flv'):
          stream_urls.append(url)
      else:
          stream_urls = getStreamUrl(url)
      # 速度默认-1
      speed = -1
      if len(stream_urls) > 0:
          # for stream in stream_urls:
          #     #print('\t流：%s' % stream)
          stream = stream_urls[0]
          downloader = Downloader(stream)
          downloadTester(downloader,minSpeed)
          speed = downloader.getSpeed()
          videoInfo=downloader.videoInfo
          if videoInfo:
              item.height=videoInfo['height']
              item.width=videoInfo['width']
          item.speed = speed
          print(f'\t速度：{item.speed} kb/s \t视频：{item.width} * {item.height} \t检测用时：{downloader.testTime}' )
          if item.speed > minSpeed and item.height>=minHeight:
              item.url=item.url+"$"+item.source
              return item
            #print(item.__json__())
      else:
          print('没有获取到视频流地址！') 
    else:
        print('\t当前地址已检测！！！')
    return None

# 符合测试结果的项目存入 result.json  item 为 Item 对象列表
def saveTojson(items,file='result.json'):
    print('当前总共地址数：',len(items))
    try:
        # 包含测试结果，存入json
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(items, f, cls=ItemJSONEncoder,ensure_ascii=False)
        # 删除相同地址
        with open(file,'r',encoding='utf-8') as f:
            result=json.load(f)
            df=pd.DataFrame(result)
            df.drop_duplicates(subset='url')

        with open(file, 'w', encoding='utf-8') as f:
            json.dump(df.to_dict(), f, cls=ItemJSONEncoder,ensure_ascii=False) 
    except BaseException as e:
        print('保存json失败 %s' % e)

#
#   根据 result.json 生成 lives configs文件
#
def creatLiveConfig(testResult='result.json',liveTxt='lives.txt',setcount=Setting().getLivesCount(),func=None):
    df=None
    lives={}
    with open(testResult, 'r', encoding='utf-8') as f:
        data=json.load(f)
        if callable(func):
            data=func(data)
        else:
            print(' 没有函数 ！')
        df=pd.DataFrame(data)
        
    if not df.empty:    
      livesModel=Setting().getLivesModel()
      for groups,value in livesModel.items():
          currentGroups={}
          for channel in value:
              name=channel.split(' ')[0] # 针对cctv
              #print('select :',name)
              if name.startswith('CCTV'):
                end=name[5:]
                if '5+' in end:
                    end='5\\+'
                #print('str end :',end)
                re_df=df[df['title'].str.contains(f'CCTV[-_]?{end}$')]
                print(f'{channel} 的行数为{len(re_df)}')
              else:
                  re_df=df[df['title'].str.contains(name)]
              #print('select result:',re_df)
              if not re_df.empty:
                  # ascending默认升序 ignore_index 保持原始索引顺序
                  #print('select result:',re_df)
                  df_sorted = re_df.sort_values(by='speed', ascending=False,ignore_index=True)
                  df_sorted=df_sorted.drop_duplicates(subset='url', keep='first')
                  adds=df_sorted['url'].to_list() 
                  currentGroups[channel]=adds
                  
                  #print(f'current {groups}',currentGroups)
                  #print(urls)
              else:
                  print(f'{channel} 没有地址！！！')
          if  any(currentGroups):
              # any 只要有一个不为空 返回True
              # all 全不为空 返回True
              lives[groups]=currentGroups
      # 生成并写入livesconfig         
      #print('livesConfig:',lives)  
      with open(liveTxt, 'w', encoding='utf-8') as f2:    
        for groups,channels in lives.items():
          if any(value for value in channels.values()):
            print(groups+',#genre#',file=f2)
            for channel,urls in channels.items():
                if urls:
                  count=len(urls) if len(urls)<setcount else setcount
                  icount=0
                  for url in urls:
                    print(channel+','+url,file=f2)
                    icount=icount+1
                    if icount==count:
                        break
            print('',file=f2)
        
            

# 从myTvbox获取 lives列表   并加本地列表      
def getLiveSource():
    list=Setting().getSourceUrls()
    url="https://gitee.com/yub168/myTvbox/raw/master/liveSource.json"
    resp=requests.get(url,headers=Setting().getHeaders())
    if resp.status_code==200:
        try:
            sourceList=resp.json()
            #print('sourceList:',sourceList)
            list.update(sourceList)
        except Exception as e:
            print('liveSource json 转换失败！',e)
    return list

def main(url=None,name=None,minSpeed=None,minHeight=None):
    
    items=[]
    list = {name if name else time.time():url} if url else getLiveSource()
    sourceBalck=Setting().getSourceBlack()
    startTime=time.time()
    num=0
    writeTestInfo(f"=========={datetime.now()}开始，共{len(list)}个地址需要测试=============")
    for key,value in list.items():
        num=num+1
        currentTime=time.time()
        if value in sourceBalck.values() :
            writeTestInfo(f'{num}.\t{key}:\t 地址已入黑名单 或已测试完成：',0)
            writeTestInfo(f'\t地址：{value}')
            continue
        print('开始测速：',value)
        sourceBalck.update({key:value})
        preItems=getAllM3UItems(value,key)
        item,count=start(preItems,minSpeed=minSpeed,minHeight=minHeight)
        if item:
          items.extend(item)
          writeTestInfo(f"{num}.\t{key}: 共{count}个地址，获取可用数量 {len(item)}",0)
          writeTestInfo(f'\t地址：{value}')
        else:
          writeTestInfo(f"{num}.\t{key}: 共{count}个地址，获取可用数量 {len(item)}",0)
          writeTestInfo(f'\t地址：{value}')
        # if len(item)<20:
        #     Setting().addSourceBlack({key:value})
        testRecord={
                    "name":key,"url":value,"acount":count,
                    "usefull":len(item),"testTime":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "useTime":round((time.time()-currentTime)/60,3)
                    }
        addtestRecord(testRecord)
    writeTestInfo(f"========== 检测总共用时: {(time.time()-startTime)//60} 分钟 =============")
    if items:
      with open('result.json', 'r', encoding='utf-8') as f:
          oldList=json.load(f)
          items.extend(oldList)
            #print('after items:',len(items))
      saveTojson(items)
      creatLiveConfig()


def reTest():
    pattern='group-title=\"(\\w+)\"'
    text='#EXTINF:-1 tvg-name="北京卫视" tvg-logo="https://live.fanmingming.com/tv/北京卫视.png" group-title="卫视频道"'
    result=re.search(pattern,text)
    print(result.group(1))

def testSource(url,name,*args):
    items,count=start(url,name,*args)
    print(f" 共{count}个地址，获取可用数量 {len(items)}")

def alayRecords():
    with open('testRecords.json',"r",encoding='utf-8') as f:
        dict = json.load(f)
        df = pd.DataFrame(dict)
        df_sorted = df.sort_values(by=['name', 'usefull'],ignore_index=True)  
        print(df_sorted)

def alayResult(path='result.json'):
    with open(path,"r",encoding='utf-8') as f:
        dict = json.load(f)
        df = pd.DataFrame(dict)
        df_sorted = df.sort_values(by='url',ignore_index=True)
        df_filter=df_sorted[['url','title','speed']]
        df_filter=df_filter.style.set_properties(**{'text-align': 'justify'})
        with open('alayResult.json','w',encoding='utf-8') as f:
            f.write(df_filter.to_string())
        #print(df_sorted)

def creatIptvTestList(sourcelist=None):
    iptvTestResult='iptvTestResult.json'
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
        finishGroups=pd.DataFrame(oldList)['groups'].to_list()
    items=[]
    # 生成测试列表 并测试 返回测试结果并添加到 test1result.json 文件中
    for key,value in sourcelist.items():
        if key not in finishGroups:
          maxCount=200
          for i in range(1,maxCount):
              item=Item()
              item.groups=key
              item.title=str(i)
              #code=format(i,'04d')
              code=str(i)
              item.url=value.format(code)
              item.source=key
              items.append(item)
        else:
            print(f'{key} 已经测试过！！！')
    return items
def translateTilte(items):
    with open('titleTranslate.json','r',encoding='utf-8') as f:
        titles=json.load(f)
        for item in items:
            # 获取需要查询的组及标题
            groups=item.get('groups')
            oldTitle=item.get('title')
            t_groups=titles.get(groups)
            #print(f'查询 {groups} : {oldTitle}')
            if t_groups:
                trueName=t_groups.get(oldTitle)
                if trueName:
                    item['title']=trueName
                else:
                    item['title']='缺省'
    return items
        
def iptvTest():
    items=creatIptvTestList()
    results,count=start(items,20,500)
    creatLiveConfig('iptvTestResult.json','iptvConfig.txt')

if __name__ == '__main__':
    
    #main()
    
    #alayRecords()
    #alayResult('test1result.json')
    creatLiveConfig('iptvTestResult.json','iptvConfig.txt',func=translateTilte)
    
   