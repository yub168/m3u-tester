import m3utester as test
from urllib.request import urlopen,Request
import requests
from m3utester import Setting,Item
import time
from datetime import datetime
import re
import pandas as pd
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

# 判断列表中的值是否包含在指定的字符串中
def isIn(list,str):
    for word in list:
        if word in str:
            return True
    return False

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
    return items       

    
# 根据配置地址生成待检测列表     
def getAllM3UItems(dir,name):
    items = []
    if dir.startswith('http'):
        try:
          resp=requests.get(dir,headers=Setting().getHeaders())
          if resp.status_code==200:
              resp.encoding='utf-8'
              if '#EXTM3U' in resp.text:
                  items=readM3u(resp,name)
              if '#genre#' in resp.text:
                  items=readText(resp,name)
          else:
              print('downLoad error!!!')
        except Exception as e:
          print('获取live配置文件错误',e)
    else:
        print('not net address!!!')
    return items

def autoScrapy(list=None,minSpeed=None,minHeight=None,testTime=None):
    startTime=time.time()
    list = list if list else getLiveSource()
    sourceBlackList=Setting().getSourceBlack()
    for key,value in list.items():
        test.writeTestInfo(f'================= 开始检测 ：{key} ==============',0)
        currentTime=time.time()
        if value in sourceBlackList.values():
            test.writeTestInfo(f'{key} 已入黑名单！！！')
            print(f'{key} 已入黑名单！！！')
            continue
        sourceBlackList.update({key:value})
        preItems=getAllM3UItems(value,key)
        if preItems:
          result=test.start(preItems,minSpeed,minHeight,testTime)
          if result:
            count=len(result)
            test.addTolivePool(result,file='scrapyResult.json')
          else:
            count=0
          test.writeTestInfo(f'\t共 {len(preItems)} 个项目, 有效个数：{count} 个,检测用时：{round((time.time()-currentTime)/60,2)}',0)
          test.writeTestInfo(f'\t地址：{value}')
        else:
            test.writeTestInfo(f'\t当前 {key} 没有获取到相关频道地址！')
        testReord={
                  "name": key,
                  "url": value,
                  "acount": len(preItems),
                  "usefull": count,
                  "testTime": time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
                  "useTime": round((time.time()-currentTime)/60,2)
                }
        test.addtestRecord(testReord)
    test.writeTestInfo(f'================    共检测用时 ：{(time.time()-startTime)//60} 分钟 =========================')   
    test.creatLiveConfig('scrapyResult.json',liveConfigTxt='scrapyConfig.txt')

if __name__ == '__main__':
    #autoScrapy({"fmbox": "http://47.99.102.252/live.txt"})
    test.creatLiveConfig('scrapyResult.json',liveConfigTxt='scrapyConfig.txt')