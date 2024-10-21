import pandas as pd
from setting import Setting
import json

def getBlackIPpool():
    '''
    获取IPtv黑名单
    '''
    with open('blackIPpool.json','r',encoding='utf-8') as f:
          urls=json.load(f)
          return urls

def addToBlackIPpool(urls):
    '''
    添加IPTV黑名单
    '''
    with open('blackIPpool.json','r',encoding='utf-8') as f:
          black_urls=json.load(f)
          if urls:
            set1=set(black_urls)
            set2=set(urls)
            set1.update(set2)
    if set1: 
      with open('blackIPpool.json','w',encoding='utf-8') as f:
              json.dump(list(set1),f,ensure_ascii=False)

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
        df=pd.DataFrame(dicts)
        result_df=df.drop_duplicates(subset=subkey,keep=keep,inplace=False)
        result=result_df.to_dict(orient='records')
    return result

def filterItems(items):
    '''
    用于筛选ipTVPool，减少测试压力
    '''
    print(f'过滤前 {len(items)} 个项目')
    # 删除url重复项目
    items=dropDuplicates(items,'url',lambda x:x.split('$')[0])
    print(f'去重后项目数:{len(items)} 个')

    # 选出tunnelkey白名单项目
    whiteKeys=Setting().getTunnelKeys()
    df=pd.DataFrame(items)
    regex_pattern = '|'.join(whiteKeys)
    df=df[df['title'].str.contains(regex_pattern)]
    print(f'白名单筛选后项目数:{len(df)} 个')

    # 删除黑名单项目
    blackIPpool=set(getBlackIPpool())
    regex_pattern = '|'.join(blackIPpool)
    df=df[df['url'].str.contains(regex_pattern)]
    print(f'黑名单筛选后项目数:{len(df)} 个')
    # filterItems=[]
    # for item in items:
    #     if item.get('url') in blackIPpool:
    #         continue
    #     filterItems.append(item)
    df.fillna('--',inplace=True)
    items=df.to_dict('records')
    print(f'过滤后 {len(items)} 个项目')
    return items

def log(content,hasBlank=0):
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

if __name__ == '__main__':
     urls=getBlackIPpool()
     result=[]
     for url in urls:
          result.extend(url.split('#'))
     addToBlackIPpool(result)