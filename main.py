import m3utester as test
import iptvTest as iptv
import scrapy 
import json

# 每星期测一次 直接运行scrapy.py
#scrapy.autoScrapy()
# 地址固定 不用常测
#iptv.autoipTvTest()

# 每天更新live池中的数据，生成最新配置文件
test.updatePoolItems('scrapyConfig.json')
test.updatePoolItems('iptvTestResult.json')
result=[]
# 合并文件
with open('scrapyResult.json','r',encoding='utf-8') as f:
  result1=json.load(f)
  if result1:
    result.extend(result1)
with open('iptvTestResult.json','r',encoding='utf-8') as f:
  result2=json.load(f)
  if result2:
    result.extend(result2)
if result:
  print('去重前数量：',len(result))
  result=test.dropDuplicates(result,'url',test.splitFilter)
  print('去重后数量：',len(result))
  test.creatLiveConfig(result,setcount=20)
else:
  print('没有检测结果！')

