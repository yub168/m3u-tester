#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: chaichunyang@outlook.com

import json
import os
import sys
import time
from urllib.request import urlopen
import requests
from func_timeout import func_set_timeout, FunctionTimedOut
from ffmpy import FFprobe
from subprocess import PIPE
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

class Item:
    def __init__(self):
        self.extinf = ''
        self.title = ''
        self.groups = ''
        self.url = ''
        self.speed = -1
        self.width = 0
        self.height = 0
        self.flagAudio = 0
        self.flagVideo = 0
        self.flagHDR = 0
        self.flagHEVC = 0

    def __json__(self):
        return {'extinf': self.extinf, 'url': self.url, 
                'groups':self.groups,'title':self.title,
                'speed': self.speed,'width':self.width,
                'height':self.height,'flagAudio':self.flagAudio,
                'flagVideo':self.flagVideo,'flagHDR':self.flagHDR,'flagHEVC':self.flagHEVC}


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

    def getSpeed(self):
        if self.endTime and self.recive != -1:
            return self.recive / (self.endTime - self.startTime)
        else:
            return -1

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
    # print('获取 %s 目录下的".m3u"文件...' % dir)
    # files = []
    # filenames = os.listdir(dir)
    # pathnames = [os.path.join(dir, filename) for filename in filenames]
    # for file in pathnames:
    #     if file.endswith('.m3u') and os.path.isfile(file):
    #         files.append(file)
    # # 解析m3u文件
    items = []
    # for file in files:
    #     with open(file, 'r+', encoding='utf-8') as f:
    #         extinf = ''
    #         for line in f:
    #             if line.startswith('#EXTM3U'):
    #                 continue
    #             if extinf:
    #                 items.append(Item(extinf.strip(), line.strip()))
    #                 extinf = ''
    #             if line.startswith('#EXTINF'):
    #                 extinf = line
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
    groupsFilter=['央视','卫视','广东','湖南']
    for line in resp.text.splitlines():
        if '#genre#' in line :
            groups=line.split(',')[0]
        elif  line and isIn(groupsFilter,groups):
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
    groupsFilter=['央视','卫视','广东','湖南']
    title=''
    lives={}
    #print('start:'+resp.text.splitlines())
    for line in resp.text.splitlines():
        if line.startswith('#EXTM3U'):
            continue
        if extinf :
            print('当前分组：',groups)
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
def get_video_info(url,item:Item):
    try:
        ffprobe = FFprobe(
            inputs={url: '-v error -show_format -show_streams -print_format json'})
        cdata = json.loads(ffprobe.run(
            stdout=PIPE, stderr=PIPE)[0].decode('utf-8'))
        #print(cdata)
        if cdata:
                flagAudio = 0
                flagVideo = 0
                flagHDR = 0
                flagHEVC = 0
                vwidth = 0
                vheight = 0
                for i in cdata['streams']:
                    if i['codec_type'] == 'video':
                        flagVideo = 1
                        if 'color_space' in i:
                            # https://www.reddit.com/r/ffmpeg/comments/kjwxm9/how_to_detect_if_video_is_hdr_or_sdr_batch_script/
                            if 'bt2020' in i['color_space']:
                                flagHDR = 1
                        if i['codec_name'] == 'hevc':
                            flagHEVC = 1
                        if vwidth <= i['coded_width']:  # 取最高分辨率
                            vwidth = i['coded_width']
                            vheight = i['coded_height']
                    elif i['codec_type'] == 'audio':
                        flagAudio = 1
                item.height=vheight
                item.width=vwidth
                item.flagAudio=flagAudio
                item.flagVideo=flagVideo
                item.flagHDR=flagHDR
                item.flagHEVC=flagHEVC

        return True
    except Exception as e:
        # traceback.print_exc()
        print('get videoInfo error:'+e)
        return False

def downloadTester(downloader: Downloader):
    chunck_size = 10240
    try:
        resp = urlopen(downloader.url, timeout=2)
        # max 5s
        while(time.time() - downloader.startTime < 5):
            chunk = resp.read(chunck_size)
            if not chunk:
                break
            downloader.recive = downloader.recive + len(chunk)
        resp.close()
    except BaseException as e:
        print("downloadTester got an error %s" % e)
        downloader.recive = -1
    downloader.endTime = time.time()


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
    return filterItem

def test(item):
    filterParams={
        'minSpeed':1024*700,
        'videoHeight':720
        }
    print('测试：%s' % item.title)
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
    item.speed = speed
    print('\t速度：%d bytes/s' % item.speed)
    if item.speed > filterParams['minSpeed']:
      get_video_info(url,item)
      if item.height>=filterParams['videoHeight']:
          #print('befroe : ',item.__json__())
          #filterItem.append(item)
          #print('filter :',filterItem[0].__json__())
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
        with open('lives.json', 'r+', encoding='utf-8') as f1:
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
                    pattern=f'{name} | "CCTV_"+{end} | "CCTV"+{end}'
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
          f1.seek(0)
          json.dump(lives,f1,ensure_ascii=False)
          # json.dump(lives, f1,ensure_ascii=False)
              
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
                   

def main():
    list={
        'fmml_ipv6':'https://iptv.b2og.com/fmml_ipv6.m3u',
        'cymz6_lives':'https://iptv.b2og.com/cymz6_lives.m3u',
        'y_g':'https://iptv.b2og.com/y_g.m3u',
        'j_home':'https://iptv.b2og.com/j_home.m3u'
        }
    items=[]
    for key,value in list.items():
        print('开始测速：',value)
        item=start(value)
        if item:
          items.extend(item)
          with open('testInfo.txt', 'a', encoding='utf-8') as f:
            print(f"{key}:获取地址数量 {len(item)}",file=f)
        else:
            with open('testInfo.txt', 'a', encoding='utf-8') as f:
              print(f"{key}:获取地址数量 0 个",file=f)
    saveTojson(items)

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
    #creatLiveJSON()
    creatLivesTXT()
    
    