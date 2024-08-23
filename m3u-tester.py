#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: chaichunyang@outlook.com
import os
import json
import time
from urllib.request import urlopen
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
    
    def addSourceBlack(self,url):
        self.setting.get('sourceBlack').append(url)
        with open('setting.json','w',encoding='utf-8') as f :
            json.dump(self.setting,f,ensure_ascii=False)
    
def downLoadM3U(url):
    response = requests.get(url)
 
    # 检查请求是否成功
    if response.status_code == 200:
        # 获取请求响应的内容
        m3u_content = response.text
    
        # 设置本地文件的文件名
        local_filename = 'downloaded_file.m3u'
    
        # 将M3U文件内容写入本地文件
        with open(local_filename, 'w',encoding='utf-8') as file:
            file.write(m3u_content)
        print(f'M3U file saved as {local_filename}')
    else:
        print('Failed to retrieve M3U file')
        
def getAllM3UItems(dir):
    
    items = []
    if dir.startswith('http'):
        resp=requests.get(dir)
        if resp.status_code==200:
            resp.encoding='utf-8'
            if '#EXTM3U' in resp.text:
                items=readM3u(resp)
            if '#genre#' in resp.text:
                items=readText(resp)
        else:
            print('downLoad error!!!')
    else:
        print('not net address!!!')
    return items

def isIn(list,str):
    for word in list:
        if word in str:
            return True
    return False

def readText(resp):
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
              item.groups=groups
              item.title=title
              item.url=url
              items.append(item)
            else:
                print('split error : '+line)
    return items
      
                
def readM3u(resp):
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
              item.url=line
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
   
def creatLives(lives,groups,title):
    if groups in lives:
        lives[groups][title]=[]
    else:
        lives[groups]={}
        lives[groups][title]=[]
        
            
def getStreamUrl(m3u8):
    urls = []
    try:
        prefix = m3u8[0:m3u8.rindex('/') + 1]
        with urlopen(m3u8, timeout=2) as resp:
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

@func_set_timeout(18)
def get_video_info(url):
    videoInfo={}
    startTime=time.time()
    #print(f"==============start ffprobe time : {time.time()}============")
    try:
      command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',url]
      process = subprocess.run(command,timeout=18,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
      # 测试用字节流
      #command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams']
      #process = subprocess.run(command,timeout=18,stdout=subprocess.PIPE,stderr=subprocess.PIPE,input=url)
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
          print("Error: ffprobe failed to execute. Return code: {}".format(process.stderr))  
      #print(f"==============stop ffprobe time : {time.time()}=============")  
      return videoInfo,time.time()-startTime
    except Exception as e:
        # traceback.print_exc()
        print('ffprobe get videoInfo error:',e)
        return False

def downloadTester(downloader: Downloader):
    #chunck_size = 10240
    #filename=str(time.time())+'.mp4'
        
    try:
        resp=requests.get(downloader.url,stream=True,timeout=2)
        content=bytes()
        for chunk in resp.iter_content(chunk_size=10240):
            if not chunk or time.time()-downloader.startTime>5:
                break
            content=content+chunk
            downloader.recive = downloader.recive + len(chunk)
        downloader.endTime = time.time()
        downloader.testTime=downloader.endTime-downloader
        if downloader.getSpeed()>Setting().getDownloadMinSpeed():
          # with open(filename,'wb') as f:
          #     f.write(content)
          videoInfo,testTime=get_video_info(downloader.url)
          downloader.testTime=downloader.testTime+testTime
          if videoInfo:
              downloader.videoInfo=videoInfo
        resp.close()
    except BaseException as e:
        print("downloadTester got an error %s" % e)
        downloader.recive = -1
    #os.remove(filename)

# 开始检测 
def start(path='https://iptv.b2og.com/j_iptv.m3u'):
    
    filterItem=[]
    #path = os.getcwd()
    items = getAllM3UItems(path)
    print('发现项: %d' % len(items))
    if len(items):
      # 循环测速 加入多线程
      with ThreadPoolExecutor(max_workers=5) as executor:
        filterItem=list(executor.map(test,items))
        filterItem=[result for result in filterItem if result is not None]
    return filterItem,len(items)

def test(item):
   
    print(f'测试：{item.groups}__{item.title}')
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
        downloadTester(downloader)
        speed = downloader.getSpeed()
        videoInfo=downloader.videoInfo
        if videoInfo:
            item.height=videoInfo['height']
            item.width=videoInfo['width']
    item.speed = speed
    print(f'\t速度：{item.speed} kb/s \t视频：{item.width} * {item.height} \t检测用时：{downloader.testTime}' )
    if item.speed > Setting().getDownloadMinSpeed() and item.height>=Setting().getVideoMinHeight():
        return item
      #print(item.__json__())
    return None

def saveTojson(item):
    print('当前总共地址数：',len(item))
    try:
        # 包含测试结果，存入json
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(item, f, cls=ItemJSONEncoder,ensure_ascii=False)
    except BaseException as e:
        print('保存json失败 %s' % e)

    # # 优质资源写入新文件
    # with open('wonderful.m3u', 'w+', encoding='utf-8') as f:
    #     print('#EXTM3U', file=f)
    #     for item in items:
    #         # 速度大于700KB
    #         if item.speed > 1024 * 700:
    #             print(item.extinf, file=f)
    #             print(item.url, file=f)
    # with open('excellent.m3u', 'w+', encoding='utf-8') as f:
    #     print('#EXTM3U', file=f)
    #     for item in items:
    #         # 速度大于1MB
    #         if item.speed > 1024 * 1024:
    #             print(item.extinf, file=f)
    #             print(item.url, file=f)

#
#   生成lives.json
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
#   生成lives.json
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
                   
def getLiveSource():
    list=Setting().getSourceUrls()
    url="https://gitee.com/yub168/myTvbox/raw/master/liveSource.json"
    resp=requests.get(url)
    if resp.status_code==200:
        try:
            sourceList=resp.json()
            #print('sourceList:',sourceList)
            list.update(sourceList)
        except Exception as e:
            print('liveSource json 转换失败！',e)
    return list
def main():
    list=getLiveSource()
    sourceBalck=Setting().getSourceBlack()
    items=[]
    startTime=time.time()
    with open('testInfo.txt', 'a', encoding='utf-8') as f:
            print(f"=========={datetime.now()}开始，共{len(list)}个地址需要测试=============",file=f)
    for key,value in list.items():
        if value in sourceBalck :
            with open('testInfo.txt', 'a', encoding='utf-8') as f:
              print(f'{key}:{value} 地址已入黑名单 或已测试完成：',file=f)
            continue
        print('开始测速：',value)
        sourceBalck.append(value)
        item,count=start(value)
        if item:
          items.extend(item)
          with open('testInfo.txt', 'a', encoding='utf-8') as f:
            print(f"{key}: 共{count}个地址，获取可用数量 {len(item)}",file=f)
            print(f'\t地址：{value}',file=f)
        else:
            with open('testInfo.txt', 'a', encoding='utf-8') as f:
              print(f"{key}: 共{count}个地址，获取可用数量 0 个",file=f)
              print(f'\t地址：{value}',file=f)
    with open('testInfo.txt', 'a', encoding='utf-8') as f:
            print(f"========== 检测总共用时: {(time.time()-startTime)//60} 分钟 =============",file=f)
    if items:
      saveTojson(items)
      if creatLiveJSON():
        creatLivesTXT()


def reTest():
    pattern='group-title=\"(\\w+)\"'
    text='#EXTINF:-1 tvg-name="北京卫视" tvg-logo="https://live.fanmingming.com/tv/北京卫视.png" group-title="卫视频道"'
    result=re.search(pattern,text)
    print(result.group(1))

def testdel():
    with open('result.json', 'r', encoding='utf-8') as f:
        data=json.load(f)
        df=pd.DataFrame(data)
        end='5\\+'
        print(df[df['title'].str.contains(f'CCTV[-_]?{end}$')])
if __name__ == '__main__':
    
    #main()
    creatLiveJSON()
    creatLivesTXT()
    #Setting().addSourceBlack('https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1718114949789/tv.txt')
    # items,count=start("https://mirror.ghproxy.com/raw.githubusercontent.com/ssili126/tv/main/itvlist.txt")
    # print(f" 共{count}个地址，获取可用数量 {len(items)}")
    
        