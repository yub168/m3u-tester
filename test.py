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
from setting import Setting
import util
pd.set_option('display.unicode.ambiguous_as_wide', True)
from dataclasses import dataclass, asdict, fields

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

# 测试项目
def test(item,testTime=None):
    # print('params speed :',minSpeed)
    # print('params height:',minHeight)
    name=item.get('source')
    print(f'测试：{name} {item.get("groups")}__{item.get("title")}')
    url = item.get('url')
    stream_urls = []
    if url.lower().endswith('.flv'):
        stream_urls.append(url)
    else:
        stream_urls = getStreamUrl(url)
    # 速度默认-1
    item['speed'] = -1
    item['height']=0
    item['width']=0
    if len(stream_urls) > 0:
        # for stream in stream_urls:
        #     #print('\t流：%s' % stream)
        stream = stream_urls[0]
        downloader = Downloader(stream)
        downloadTester(downloader,testTime)
        speed = downloader.getSpeed()
        videoInfo=downloader.videoInfo
        if videoInfo:
            item['height']=videoInfo['height']
            item['width']=videoInfo['width']
        item['speed'] = speed
    else:
        print('没有获取到视频流地址！') 
    return item


# 符合测试结果的项目存入 result.json  item 为 Item 对象列表
def saveToTestPool(items,file='testResultPool.json',add=1):
    print('当前总共地址数：',len(items))
    if items:
      try:
        # if add:
        #   with open(file,'r',encoding='utf-8') as f:
        #     result=json.load(f)
        #     if result:
        #       result.extend(dictList)
        #     else:
        #       result=dictList
        # else:
        #     result=dictList
        
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False) 
    
      except BaseException as e:
        print('保存json失败 %s' % e)
      
# 开始检测单一地址可用数量 
def testMore(items,minSpeed=None,minHeight=None,testTime=None):
    '''
      ### Params
      1. items : 待检测的 Item dict列表
      2. minSpeed : 检测合格的最低速度
      3. minHeight : 检测合格的视频最小height
      4. testTime : 检测速度时下载最长时长，缺省为 5
      ### Return
      1. list: 返回 合格的 Item类list列表
      
    '''
    if not minHeight:
        minHeight=Setting().getVideoMinHeight()
    if not minSpeed:
        minSpeed=Setting().getDownloadMinSpeed()
    resultItem=[]
    items = util.filterItems(items)
    print(f'共 {len(items)} 项需要检测！')
    if len(items):
      # 循环测速 加入多线程
      with ThreadPoolExecutor(max_workers=6) as executor:
        tesItem=list(executor.map(test,items,len(items)*[testTime]))
        df = pd.DataFrame(tesItem)
        ok_df = df[(df['speed']>=minSpeed) & (df['height']>=minHeight)]
        resultItem = ok_df.to_dict('records')
        saveToTestPool(resultItem)
        black_df = df[(df['speed']<minSpeed) | (df['height']<=minHeight)]
        black_urls=black_df['url'].to_list()
        util.addToBlackIPpool(black_urls)
    return resultItem

def testLocalPool():
    with open('ipTVPool.json','r',encoding="utf-8") as f:
        list=json.load(f)
    if list:
        result=testMore(list)
        return result

#
#   根据 result.json 生成 lives configs文件
#
def creatLiveConfig(testResult:str | list='testResultPool.json',liveConfigTxt='lives.txt',setcount=Setting().getLivesCount()):
    '''
    根据 testResultPool.json 生成 lives configs文件
    '''
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
                      adds=(df_sorted['url']+'$'+df_sorted['source']).to_list() 
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
            print(f'// 更新于：{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())}',file=f2)
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
    else:
        print('没有检测结果！')   

if __name__ == '__main__':
    testLocalPool()
    creatLiveConfig()

    
    