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

class Item:
    def __init__(self):
        self.extinf = ''
        self.title = ''
        self.groups = ''
        self.url = ''
        self.speed = -1
        self.width = 0
        self.height = 0
        

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

# 判断列表中的值是否包含在指定的字符串中
def isIn(list,str):
    for word in list:
        if word in str:
            return True
    return False

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
              url=line.split(',')[1]
              if '$' not in url:
                  url=url+'$'+name
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
              if '$' not in line:
                  url=line+'$'+name
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
def start(path='https://iptv.b2og.com/j_iptv.m3u',name=None,minSpeed=None,minHeight=None):
    
    filterItem=[]
    #path = os.getcwd()
    items = getAllM3UItems(path,name)
    print('发现项: %d' % len(items))
    if len(items):
      # 循环测速 加入多线程
      with ThreadPoolExecutor(max_workers=6) as executor:
        filterItem=list(executor.map(test,items,len(items)*[minSpeed],len(items)*[minHeight]))
        filterItem=[result for result in filterItem if result is not None]
    return filterItem,len(items)

# 测试项目
def test(item,minSpeed=None,minHeight=None):
    # print('params speed :',minSpeed)
    # print('params height:',minHeight)
    print(f'测试：{item.groups}__{item.title}')
    if not minHeight:
        minHeight=Setting().getVideoMinHeight()
    if not minSpeed:
        minSpeed=Setting().getDownloadMinSpeed()
    url = item.url
    #print('地址：%s' % url)
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
            return item
          #print(item.__json__())
    return None

# 符合测试结果的项目存入 result.json
def saveTojson(item):
    print('当前总共地址数：',len(item))
    try:
        # 包含测试结果，存入json
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(item, f, cls=ItemJSONEncoder,ensure_ascii=False)
    except BaseException as e:
        print('保存json失败 %s' % e)

#
#   根据 result.json 生成 lives.json
#
def creatLiveJSON():
    with open('result.json', 'r', encoding='utf-8') as f:
        data=json.load(f)
        df=pd.DataFrame(data)
        if df.empty:
          return False
        lives={}
        with open('lives.json', 'r', encoding='utf-8') as f1:
            lives=json.load(f1)
            for groups,value in lives.items():
                for channle,urls in value.items():
                    name=channle.split(' ')[0]
                    #print('select :',name)
                    if name.startswith('CCTV'):
                      end=name[5:]
                      if '5+' in end:
                          end='5\\+'
                      #print('str end :',end)
                      re_df=df[df['title'].str.contains(f'CCTV[-_]?{end}$')]
                      print(f'{channle} 的行数为{len(re_df)}')
                    else:
                        re_df=df[df['title'].str.contains(name)]
                    #print('select result:',re_df)
                    if not re_df.empty:
                        # ascending默认升序 ignore_index 保持原始索引顺序
                        #print('select result:',re_df)
                        df_sorted = re_df.sort_values(by='speed', ascending=False,ignore_index=True)
                        df_sorted=df_sorted.drop_duplicates(subset='url', keep='first')
                        adds=df_sorted['url'].to_list() 
                        # print('urls count ：',len(urls))
                        # print('new  count ：',len(adds))
                        lives[groups][channle]=adds
                        # print('CCTV1 count',len(lives[groups][channle]))
                        #print(urls)
                    else:
                        print(f'{channle} 没有地址！！！')
            # 从起位置写入
        if lives:
            with open('lives.json', 'w', encoding='utf-8') as f1:
              f1.seek(0)
              json.dump(lives,f1,ensure_ascii=False)
              return True
        
            
              
#
#   根据lives.json 生成lives.txt 节目表
#
def creatLivesTXT():
    with open('lives.json', 'r', encoding='utf-8') as f1:
          lives=json.load(f1)
          with open('lives.txt', 'w', encoding='utf-8') as f2:
            for groups,channels in lives.items():
                if any(value for value in channels.values()):
                  print(groups+',#genre#',file=f2)
                  for channel,urls in channels.items():
                      if urls:
                        count=len(urls) if len(urls)<8 else 8
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
    
    writeTestInfo(f"=========={datetime.now()}开始，共{len(list)}个地址需要测试=============",0)
    for key,value in list.items():
        if value in sourceBalck.values() :
            writeTestInfo(f'{key}:\t 地址已入黑名单 或已测试完成：',0)
            writeTestInfo(f'\t地址：{value}')
            continue
        print('开始测速：',value)
        sourceBalck.update({key:value})
        item,count=start(value,key,minSpeed=minSpeed,minHeight=minHeight)
        if item:
          items.extend(item)
          writeTestInfo(f"{key}: 共{count}个地址，获取可用数量 {len(item)}",0)
          writeTestInfo(f'\t地址：{value}')
        else:
          writeTestInfo(f"{key}: 共{count}个地址，获取可用数量 {len(item)}",0)
          writeTestInfo(f'\t地址：{value}')
        if len(item)<20:
            Setting().addSourceBlack({key:value})
        testRecord={"name":key,"url":value,"acount":count,"usefull":len(item),"testTime":time.time()}
        addtestRecord(testRecord)
    writeTestInfo(f"========== 检测总共用时: {(time.time()-startTime)//60} 分钟 =============",0)
    
    if items:
      if url:
          with open('result.json', 'r', encoding='utf-8') as f:
              oldList=json.load(f)
              items.extend(oldList)
              print('after items:',len(items))
      saveTojson(items)
      if creatLiveJSON():
        creatLivesTXT()


def reTest():
    pattern='group-title=\"(\\w+)\"'
    text='#EXTINF:-1 tvg-name="北京卫视" tvg-logo="https://live.fanmingming.com/tv/北京卫视.png" group-title="卫视频道"'
    result=re.search(pattern,text)
    print(result.group(1))

def testSource(url,*args):
    items,count=start(url,*args)
    print(f" 共{count}个地址，获取可用数量 {len(items)}")

if __name__ == '__main__':
    
    main()
    # creatLiveJSON()
    # creatLivesTXT()
    #testSource("https://xn--tkh-mf3g9f.v.nxog.top/m/tv/1/",2000,1080)
    