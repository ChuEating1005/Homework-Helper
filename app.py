# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 21:16:35 2021

@author: Ivan
版權屬於「行銷搬進大程式」所有，若有疑問，可聯絡ivanyang0606@gmail.com

Line Bot聊天機器人
第一章 Line Bot申請與串接
Line Bot機器人串接與測試
"""
#載入LineBot所需要的套件
from flask import Flask, request, abort
import os
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

import tempfile

from pdf_processor import process_pdf_file

app = Flask(__name__)

# 必須放上自己的Channel Access Token
line_bot_api = LineBotApi('9hDQFa2YiPRhlPPm+mE4DOdjBVJ62Nf2MekyiecaFFMKH3n9LxiiNTGwNjlH4Q4fxyoz+rU8yBb+QFoupFlI3wn0VUhWbq4tZoxgbx6xj1cxjnCpihFcvUM8HtRUj+RANUOK5I/63fDIV8kfubdTTwdB04t89/1O/w1cDnyilFU=')
# 必須放上自己的Channel Secret
handler = WebhookHandler('946262b6de4a50790330570dc37e6b3b')

line_bot_api.push_message('Udb9f6efb644b35a32f17265476f9a2dc', TextSendMessage(text='你可以開始了'))

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
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

#訊息傳遞區塊
##### 基本上程式編輯都在這個function #####
@handler.add(MessageEvent, message=FileMessage)
def handle_message(event):
    # message = TextSendMessage(text=event.message.text)
    # line_bot_api.reply_message(event.reply_token,message)
    file_message = event.message
    file_content = line_bot_api.get_message_content(file_message.id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        for chunk in file_content.iter_content():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
        
    # Process the PDF file
    try:
        response = process_pdf_file(temp_file_path)
        reply_message = TextSendMessage(text=response)
    except Exception as e:
        reply_message = TextSendMessage(text=f"Failed to process the PDF file: {str(e)}")
    finally:
        os.remove(temp_file_path)  # Clean up the temporary file
        
   # reply_message = TextSendMessage(text="Received file: " + file_message.file_name)
    line_bot_api.reply_message(event.reply_token, reply_message)

#主程式
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)