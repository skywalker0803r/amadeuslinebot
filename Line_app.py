# -*- coding: utf-8 -*-
from flask import Flask, request, abort
import requests
import json
from linebot import (
    LineBotApi, WebhookHandler
)
import time
from nlp.olami import Olami
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage ,SourceUser
)
from linebot.models import *
import pandas as pd
import configparser
import datetime
import numpy as np

import requests
from bs4 import BeautifulSoup

from draw_rader import pie_graph
#from Generate_line_graph import predict_line_graph
#取得金融數據歷史資料
from finlab.data import Data
data=Data()

# 取得所有策略
import os
snames = [py for py in os.listdir('strategies') if py[-3:] == '.py' and py != '__init__.py']
strategies = {}
for s in snames:
    strategies[s[:-3]] = getattr(__import__('strategies.' + s[:-3]), s[:-3]).strategy

# substringSieve
def substringSieve(string_list):
  string_list.sort(key=lambda s: len(s), reverse=True)
  out = []
  for s in string_list:
    if not any([s in o for o in out]):
      out.append(s)
  return out

# MSKTS
from simhash import Simhash
import joblib

class MSKTS(object):
  '''
  most similar k text search
  '''
  def __init__(self):
    self.name = 'most similar k text search'
  
  def fit(self,database):
    self.database = map(lambda x:str(x).lower(),database)
  
  def predict(self,input_data,k=3):
    input_data = input_data.lower()
    score = {}
    for history_data in self.database:
      score[history_data] = Simhash(input_data).distance(Simhash(history_data))
    return sorted(score.items(),key=lambda x:x[1],reverse=False)[:k]

#模擬的函數
def simulation(strategy):
    slist = strategy(data).index
    return slist


#輸入策略名稱返回股票清單的函數
def get_slist(strategy_name):
    c = ''
    strategy=strategies[strategy_name]
    res = simulation(strategy)
    row = '{}\n{}\n'.format(strategy_name,res.tolist())
    c += row
    return c

#查看目前資料庫日期
def get_DBdate(data):
    c= ''
    row = '{}\n{}\n'.format('目前資料庫日期',str(data.date))
    c += row
    return c

#爬玩股網
def wantgoo(sid):
    target_url = 'https://www.wantgoo.com/stock/'+sid
    rs = requests.session()
    res = rs.get(target_url)#verify=False
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ''
    if len(soup.select('.cn div'))!=0:
        for titleURL in soup.select('.cn div'):
            title = titleURL.text.replace(' ','').replace('\n','').replace('\r','')
            data = '{}\n'.format(title)
            content += data
    else:
        content += '沒有搜尋到匹配的股票'
    return '{}\n{}'.format(sid,content)

app = Flask(__name__,static_url_path = "/images" , static_folder = "./images/" )

#Line的一些使用者金鑰設定
config = configparser.ConfigParser()
config.read("config.ini")
line_bot_api = LineBotApi(config['line_bot']['Channel_Access_Token'])
handler = WebhookHandler(config['line_bot']['Channel_Secret'])

import json
secretFileContentJson=json.load(open("./line_secret_key",'r'))
server_url=secretFileContentJson.get("server_url")

#定義路由器
@app.route("/", methods=['POST'])
def index():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


#定義接收到文字訊息要如何處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
#=======================================================================================
    if event.message.text == 'profile':
        if isinstance(event.source, SourceUser):
            profile = line_bot_api.get_profile(event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(text='Display name: ' + profile.display_name),
                    TextSendMessage(text='Status message: ' + profile.status_message)
                ]
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Bot can't use profile API without user ID"))
#=======================================================================================
    elif event.message.text == 'image':
        url='https://%s/images/logo.png'% server_url
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(original_content_url=url, preview_image_url=url)
        )
#=======================================================================================
    host_id="Uc13726ca34cc65314694bad1cb6b7394"
#=======================================================================================
    if event.source.user_id!=host_id:
        if event.source.type=='group':
            group_id=event.source.group_id
            group_text=event.message.text+'\n'+'from'+'\n'+group_id
            line_bot_api.push_message(host_id,TextSendMessage(text=group_text))
        else:
            guest_id=event.source.user_id
            guest_text=event.message.text+'\n'+'from'+'\n'+guest_id
            line_bot_api.push_message(host_id,TextSendMessage(text=guest_text))
#=======================================================================================
    if (event.source.user_id==host_id) and (event.message.text.split(':')[0]=='@傳訊'):
        host_text=event.message.text
        To_userid=host_text.split(':')[1]
        My_message=host_text.split(':')[2:]
        content=""
        for i in My_message:
            content+=i
        line_bot_api.push_message(To_userid,TextSendMessage(text=content))
#=======================================================================================
    if (event.source.user_id==host_id) and (event.message.text.split(':')[0]=='@取得個資'):
        user_id=event.message.text.split(':')[1]
        profile = line_bot_api.get_profile(user_id)
        line_bot_api.reply_message(event.reply_token,[
            TextSendMessage(text='Display name: ' + str(profile.display_name)),
            TextSendMessage(text='Status message: ' + str(profile.status_message)),
            TextSendMessage(text='Photo url: ' + str(profile.picture_url))])
#========================================================================================
    elif (event.message.text.split(' ')[0]=="技術健診") and (len(event.message.text.split(' '))==2):
        sid=event.message.text.split(' ')[1]
        content=wantgoo(sid)
        line_bot_api.reply_message(event.reply_token,TextSendMessage(content))

    elif (event.message.text.split(' ')[0]=="財報健診") and (len(event.message.text.split(' '))==2):
        sid=event.message.text.split(' ')[1]
        try:
            pie_graph(sid)#繪圖並保存
            img_url='https://%s/images/'% server_url
            line_bot_api.reply_message(event.reply_token,ImageSendMessage(
            original_content_url=img_url+sid+'.png',
            preview_image_url=img_url+sid+'.png'))
        except:
        	line_bot_api.reply_message(event.reply_token,TextSendMessage('沒有搜尋到匹配的股票'))

    #elif (event.message.text.split(' ')[0]=="走勢預測") and (len(event.message.text.split(' '))==2):
        #sid=event.message.text.split(' ')[1]
        #try:
            #predict_line_graph(sid)#繪圖並保存
            #img_url='https://%s/images/'% server_url
            #line_bot_api.reply_message(event.reply_token,ImageSendMessage(
            #original_content_url=img_url+sid+'_fbprop'+'.png',
            #preview_image_url=img_url+sid+'_fbprop'+'.png'))
        #except:
            #line_bot_api.reply_message(event.reply_token,TextSendMessage('沒有搜尋到匹配的股票'))
    
    elif event.message.text =="查看資料庫日期":
        content=get_DBdate(data)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))

    elif event.message.text =="均線大挪移":
        content = get_slist('均線大挪移')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
    
    elif event.message.text =="鳴槍起漲強勢股":
        content = get_slist('鳴槍起漲強勢股')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
#=========================================    
    #elif event.message.text =="Alpha":
        #content = get_slist('Alpha')
        #line_bot_api.reply_message(
            #event.reply_token,
            #TextSendMessage(content))
#========================================    
    elif event.message.text =="資優生策略_改":
        content = get_slist('資優生策略_改')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
    elif event.message.text =="MFPiot":
        content = get_slist('MFPiot')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
    
    #選單=========================================================================================================
    elif event.message.text == "選股":
        buttons_template = TemplateSendMessage(
            alt_text='選股 template',
            template=ButtonsTemplate(
                title='服務類型',
                text='請選擇',
                thumbnail_image_url='https://2.bp.blogspot.com/-H5Qu0dggSKM/XEAfo9p-2-I/AAAAAAAAAkw/00FW3zikCB84ECzKJzJicUS34ykUI7iRACLcBGAs/s1600/ok2.png',
                actions=[
                    MessageTemplateAction(
                        label='均線大挪移',
                        text='均線大挪移'
                    ),
                    MessageTemplateAction(
                        label='鳴槍起漲強勢股',
                        text='鳴槍起漲強勢股'
                    ),
                    #MessageTemplateAction(
                        #label='Alpha',
                        #text='Alpha'
                    #),
                    MessageTemplateAction(
                        label='資優生策略_改',
                        text='資優生策略_改'
                    ),
                    MessageTemplateAction(
                        label='MFPiot',
                        text='MFPiot'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    #新功能==============================================================================================
    elif (event.message.text in ["我愛妳","我愛你"])&(event.source.user_id==host_id):
        content = '我也是>///<,最愛Ricky了'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
    elif (event.message.text in ["報數"])&(event.source.user_id==host_id):
        content = '機器人#金融&情報收集特化型 no.1'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(content))
    elif (event.source.user_id==host_id) and (event.message.text.split(':')[0]=='@最相似文本搜索'):
        host_text = event.message.text
        message = host_text.split(':')[1]
        
        # 產生data
        try:
            data = pd.read_csv('data.csv')
        except:
            data = pd.DataFrame(columns=['txt'],index=[0])
            data.loc[0,'txt'] = '我們在天上的父，願人都尊你的名為聖，願你的國降臨，願你的旨意行在地上如同行在天上，我們日用的飲食，今日賜給我們，免我們的債，如同我們免了人的債，不叫我們陷入試探，救我們脫離兇惡，因為國度、權柄、榮耀全是你的，直到永遠。'
        
        # 擴充data
        new_index = data.index[-1]+1
        data.loc[new_index,'txt'] = message

        # 確認沒有重複
        data2 = pd.DataFrame()
        data2['txt'] = substringSieve(data['txt'].values.tolist())
        data = data2
        
        # 保存data
        data.to_csv('data.csv')

        # 使用model訓練跟預測
        model = MSKTS()
        model.fit(data['txt'].values.tolist())
        content = model.predict(message)[0][0]
        line_bot_api.reply_message(event.reply_token,TextSendMessage(content))
        
    #=====================================================================================================
    #elif(event.message.text != "個股健診")&(event.message.text != "選股")&(event.message.text != "走勢預測"):
        #串接智能聊天API
        #content=Olami().nli(event.message.text,event.source.user_id)
        #if content!=0:
        #    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=content))

#run
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=2336, debug=True)
