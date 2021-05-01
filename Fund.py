import queue
import threading

import requests
import time
import execjs
import csv
from queue import Queue,LifoQueue,PriorityQueue
from threading import Lock,Thread

start=time.time()
funddata=queue.Queue(maxsize=30000)
#获得所有基金数据
def getAllCode():
    url1 = 'http://fund.eastmoney.com/js/fundcode_search.js'
    content = requests.get(url1)
    jsContent = execjs.compile(content.text)
    rawData = jsContent.eval('r')
    allCode = queue.Queue(maxsize=30000)
    for code in rawData:
        if(allCode.qsize()<100):
            allCode.put(code[0])
            funddata.put(code[3])
    return allCode
allCode = getAllCode()

def getUrl(fscode):
  head = 'http://fund.eastmoney.com/pingzhongdata/'
  tail = '.js?v='+ time.strftime("%Y%m%d%H%M%S",time.localtime())
  return head+fscode+tail

# 根据基金代码获取净值
def getData(fscode):
    content = requests.get(getUrl(fscode))
    jsContent = execjs.compile(content.text)
    name = jsContent.eval('fS_name')
    code = jsContent.eval('fS_code')
    # 基金类型
    # type=funddata[allCode.find(fscode)][1]
    #近七个交易日
    netWorthTrend = jsContent.eval('Data_netWorthTrend')
    #近一年收益率
    YearSyl =jsContent.eval('syl_1n')
    #近六月收益率
    SMonthSyl=jsContent.eval('syl_6y')
    #近三月收益率
    TMonthSyl=jsContent.eval('syl_3y')
    #近一月收益率
    OMonthSyl=jsContent.eval('syl_1y')
    print(name,code)
    netWorth=[]
    for dayWorth in netWorthTrend[::-1]:
        netWorth.append(dayWorth['y'])
    return name,netWorth,YearSyl, SMonthSyl,TMonthSyl,OMonthSyl

num=0
FundDataFile= open('data.csv','w')
csvwriter = csv.writer(FundDataFile);
csvwriter.writerow(["基金代码", "基金类型","近七个交易日收益","近一月收益", "近三月收益", "近六月收益", "近一年收益","连涨/跌天数"])

mylock=threading.Lock()
def RunFundData():
    while (not allCode.empty()):
        code = allCode.get()
        try:
            name, netWorth, YearSyl, SMonthSyl, TMonthSyl, OMonthSyl = getData(code)
        except:
            continue
        if len(YearSyl) <= 0 and len(SMonthSyl) <= 0 and len(TMonthSyl) <= 0 and len(OMonthSyl) <= 0:
            print("基金" + code + "数据暂无。")
            continue
        if len(netWorth) < 8:
            print("基金" + code + "数据暂无。")
            continue
        WeekSyl = (netWorth[0] - netWorth[6]) / netWorth[6] * 100
        flag = 0
        rise = 0
        dice = 0
        len1 = len(netWorth) if len(netWorth) < 10 else 10
        for i in range(0, len1 - 1):
            if netWorth[i] >= netWorth[i + 1] and flag <= 0:
                rise = rise + 1
            if netWorth[i] <= netWorth[i + 1] and flag >= 0:
                dice = dice - 1
            if netWorth[i] >= netWorth[i + 1] and flag >= 0 and dice < 0:
                break
            if netWorth[i] <= netWorth[i + 1] and flag >= 0 and rise > 0:
                break
        type = funddata.get()
        maxx = rise if abs(rise) > abs(dice) else dice
        try:
            mylock.acquire();
            csvwriter.writerow([name + '(' + str(code.zfill(6)) + ')', type, str(WeekSyl) + '%', OMonthSyl + '%', TMonthSyl + '%',SMonthSyl + '%', YearSyl + '%', str(maxx)])
        finally:
            mylock.release()
        print("write " + code + "'s data success.")

mutex_lock=threading.Lock()
for i in range(16):
    t=threading.Thread(target=RunFundData(),name='LoopThread'+str(i))
    t.start()
FundDataFile.close()
end=time.time()
print('运行时间为: %s 秒'%(end-start))
