import json
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
    def getTunnelKeys(self):
        return self.setting.get('tunnelKeys')