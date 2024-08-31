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
from dataclasses import dataclass, asdict, fields
#pd.set_option('display.unicode.east_asian_width', True)
#pd.set_option('display.unicode.east_asian_width', True)

@dataclass
class Item:
    def __init__(self,**kwargs):
        self.extinf = ''
        self.title = ''
        self.groups = ''
        self.url = ''
        self.speed = -1
        self.width = 0
        self.height = 0
        self.source=''
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __json__(self):
        return {'extinf': self.extinf, 'url': self.url, 
                'groups':self.groups,'title':self.title,
                'speed': self.speed,'width':self.width,
                'height':self.height,'source':self.source}


class ItemJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)

class ItemJSONDecoder(json.JSONDecoder):
    def decode(self, s):
        obj=super().decode(s)
        items=[]
        for item in obj:
            items.append(Item(**item))
        return items
        
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
    def getTestTime(self):
        return self.setting.get('testTime')

# 写入测试记录  
def addtestRecord(item):
    testRecords=[]
    with open('testRecords.json','r',encoding="utf-8") as f:
        testRecords=json.load(f)
        testRecords.append(item)
    with open('testRecords.json','w',encoding="utf-8") as f:
        json.dump(testRecords,f,ensure_ascii=False)


def writeTestInfo(content,hasBlank=1):
    '''
      写入测试信息
      ### parama
      content ： 要写入的信息
      hasBlank : 1 后面插入一空行
    '''
    with open('testInfo.txt', 'a', encoding='utf-8') as f:
        print(content,file=f)
        if hasBlank:
            print('',file=f)

def ItemsToDicts(items):
    '''
      ### 将 Item 列表转换成 Dict 列表 
    '''
    if items:
        try:
          result=[]
          for item in items:
              dict=item.__json__()
              result.append(dict)
          return result
        except Exception as e:
            print('Item列表转Dict列表错误：',e)
    else:
        print('ItemsToDicts: 没有发现可转换的对象！！ ')
    return None

def  DictsToItems(dicts):
    '''
      ### 将 Dict 列表转换成 Items 列表 
    '''
    if dicts:
        try:
          result=[]
          for dict in dicts:
            result.append(Item(**dict))
          return alayResult
        except Exception as e:
            print('Dict列表转Item列表错误：',e)
    return None

def splitFilter(str):
    return str.split('$')[0]

def dropDuplicates(dicts,subkey,cls=None,keep="last"):
    '''
     用于筛选删除指定字段值只有部份相同的项
     ### Params
     dicts : 字典列表
     subKey ：去重字段
     cls : 用来返回需要去重的关键字符串
     keep : 保留哪一个
     inplace : 
          True : 直接在原数据上修改
          False : 返回修改后的副本
    '''
    result_dict={}
    key_dict={}
    if callable(cls):
        index=0
        for dict in dicts:
            url=cls(dict[subkey])
            if url in key_dict.keys():
                if keep=='fast':
                    index=index+1
                    continue
                result_dict[key_dict[url]]=dict
                index=index+1
            else:
                key_dict.update({url:index})
                result_dict.update({index:dict})
                index=index+1
            #print('result dicts:',result_dict)
        result=result_dict.values()
    else:
        df=pd.DataFrame(dict)
        result_df=df.drop_duplicates(subset=subkey)
        result=result_df.to_dict(orient='records')
    return result
        

        
        
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
def downloadTester(downloader: Downloader,testTime=None):
    if not testTime:
        testTime=Setting().getTestTime()
    try:
        resp=requests.get(downloader.url,stream=True,timeout=2,headers=Setting().getHeaders())
        content=bytes()
        for chunk in resp.iter_content(chunk_size=10240):
            if not chunk or (time.time()-downloader.startTime)>testTime:
                break
            content=content+chunk
            downloader.recive = downloader.recive + len(chunk)
        downloader.endTime = time.time()
        downloader.testTime=downloader.endTime-downloader.startTime
        if downloader.getSpeed()>-1:
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
def start(items,minSpeed=None,minHeight=None,testTime=None):
    '''
      ### Params
      1. items : 待检测的 Item 类列表
      2. minSpeed : 检测合格的最低速度
      3. minHeight : 检测合格的视频最小height
      4. testTime : 检测速度时下载最长时长，缺省为 5
      ### Return
      1. list: 返回 合格的 Item类list列表
      
    '''
    filterItem=[]
    print(f'共 {len(items)} 项需要检测！')
    if len(items):
      # 循环测速 加入多线程
      with ThreadPoolExecutor(max_workers=6) as executor:
        filterItem=list(executor.map(test,items,len(items)*[minSpeed],len(items)*[minHeight],len(items)*[testTime]))
        filterItem=[result for result in filterItem if result is not None]
    if filterItem:
        filterItem=ItemsToDicts(filterItem)
    return filterItem

# 防止重复项目
finishedUrls=set()
# 测试项目
def test(item,minSpeed=None,minHeight=None,testTime=None):
    # print('params speed :',minSpeed)
    # print('params height:',minHeight)
    name=item.source
    print(f'测试：{name} {item.groups}__{item.title}')
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
          downloadTester(downloader,testTime)
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
def addTolivePool(items,file='livePool.json',add=1):
    print('当前总共地址数：',len(items))
    if items:
      dictList=items
      if dictList:
        try:
          if add:
            with open(file,'r',encoding='utf-8') as f:
              result=json.load(f)
              if result:
                result.extend(dictList)
              else:
                result=dictList
          else:
              result=dictList
          #print(' addToLivePool：',result)
          with open(file, 'w', encoding='utf-8') as f:
              json.dump(result, f, ensure_ascii=False) 
      
        except BaseException as e:
          print('保存json失败 %s' % e)
      else:
          print(' ')

# 用于IpTv编号转台名
def translateTilte(items):
    '''
      items : 为dict列表
    '''
    if items:
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
    return items
#
#   根据 result.json 生成 lives configs文件
#
def creatLiveConfig(testResult:str | list=None,liveConfigTxt='lives.txt',setcount=Setting().getLivesCount()):
    df=None
    lives={}
    if type(testResult)==str:
        with open(testResult,'r',encoding='utf-8') as f:
            liveItems=json.load(f)
    else:
        liveItems=testResult
    if liveItems:
        df=pd.DataFrame(liveItems)
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
              else:
                  re_df=df[df['title'].str.contains(name)]
              #print('select result:',re_df)
              if not re_df.empty:
                  print(f'{channel} 的行数为 {len(re_df)}')
                  # ascending默认升序 ignore_index 保持原始索引顺序
                  #print('select result:',re_df)
                  df_sorted = re_df.sort_values(by='speed', ascending=False,ignore_index=True)
                  df_sorted.drop_duplicates(subset='url', keep='first',inplace=True)
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
      with open(liveConfigTxt, 'w', encoding='utf-8') as f2:    
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
        
            
def reTest():
    pattern='group-title=\"(\\w+)\"'
    text='#EXTINF:-1 tvg-name="北京卫视" tvg-logo="https://live.fanmingming.com/tv/北京卫视.png" group-title="卫视频道"'
    result=re.search(pattern,text)
    print(result.group(1))



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

# 用于对 项目池中的项目重测更新速度数据
def updatePoolItems(file='result.json',update=1):
    '''
    ### Params
      file : 要检测的项目文件
      update : 是否把检测结果更新到文件
    '''
    #try:
    with open(file,'r',encoding='utf-8') as f:
        items=json.load(f)
        if items:
          items=dropDuplicates(items,'url',splitFilter,keep='last')
          items=DictsToItems(items)
          #print(items)
          result=start(items,minSpeed=300,minHeight=720,testTime=10)
          print(f'共检测 {len(items)} 个，有效数量 {len(result)} 个。')
    if update and result:
      with open(file,'w',encoding='utf-8') as f:
          json.dump(result,f,cls=ItemJSONEncoder,ensure_ascii=False)
    # except BaseException as e:
    #     print('检测异常：',e)


if __name__ == '__main__':
    
    #main()
    #alayRecords()
    #alayResult('test1result.json')
    #creatLiveConfig('iptvTestResult.json','iptvConfig.txt',func=translateTilte)
    updatePoolItems('iptvTestResult.json',0)
    