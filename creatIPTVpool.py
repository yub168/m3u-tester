
import requests
from setting import Setting
import re
import json
import util

def getLiveConfigs():
  '''
    从myTvbox liveSource和本地设置中获取lives列表
    # return list:dict
      {
        "欧歌_ipv4v6": "https://tv.nxog.top/m/tv/1/",
        "欧歌_app": "https://tv.nxog.top/m/tv/"
      }
  '''
  list=Setting().getSourceUrls()
  url="https://mirror.ghproxy.com/https://github.com/yub168/myTvbox/raw/refs/heads/master/liveSource.json"
  resp=requests.get(url,headers=Setting().getHeaders())
  if resp.status_code==200:
      try:
          sourceList=resp.json()
          #print('sourceList:',sourceList)
          list.update(sourceList)
      except Exception as e:
          print('liveSource json 转换失败！',e)
  return list

def pariseM3uConfig(content,source):
    '''
    解析M3u类型文件
    '''
    items=[]
    extinf = ''
    for line in content.splitlines():
        
        if line.startswith('#EXTM3U'):
            continue
        if extinf :
            #print('当前分组：',groups)
            url=line.split('$')[0]
            urls=url.split('#')
            for url in urls:
              item={}
              item['extinf']=extinf
              item['groups']=groups
              item['title']=title
              item['source']=source
              item['url']=url
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

def pariseTextConfig(content,source):
    '''
    解析Txt类型文件
    '''
    items=[]
    groups = ''
    for line in content.splitlines():
        if '#genre#' in line :
            groups=line.split(',')[0]
        elif  line:
            #print('符合分组：',line)
            item={}
            info=line.split(',')
            if len(info)>1:
              title=line.split(',')[0]
              urlStr=line.split(',')[1]
              if urlStr:
                  url=urlStr.split('$')[0]
                  urls=url.split('#')
                  for url in urls:
                    item={}
                    item['groups']=groups
                    item['title']=title
                    item['source']=source
                    item['url']=url
                    items.append(item)
            else:
                print('split error : '+line)
    return items

def getLives(url,source):
    items = []
    if url.startswith('http'):
        try:
          resp=requests.get(url,headers=Setting().getHeaders())
          if resp.status_code==200:
              resp.encoding='utf-8'
              if '#EXTM3U' in resp.text:
                  items=pariseM3uConfig(resp.text,source)
              if '#genre#' in resp.text:
                  items=pariseTextConfig(resp.text,source)
          else:
              print('downLoad error!!!')
        except Exception as e:
          print('获取live配置文件错误',e)
    else:
        print('not net address!!!')
    return items



def creatIPTVPool(list):
    items = []
    finishLives=[]
    for key,value in list.items():
        print(f'开始抓取 {key} ：{value}')
        if value in finishLives:
            continue
        lives = getLives(value,key)
        if lives:
            items.extend(lives)
        finishLives.append(value)
    if items:
        # 添加去重和关键字筛选
        items= util.filterItems(items)
        with open('ipTVPool.json', 'w', encoding='utf-8') as f:
              json.dump(items, f, ensure_ascii=False) 

def start():
    configs= getLiveConfigs()
    if configs:
        creatIPTVPool(configs)

if __name__ == '__main__':
    start()