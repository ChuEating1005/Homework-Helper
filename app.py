# -*- coding: utf-8 -*-
#載入LineBot所需要的套件
from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import tempfile

from openAI_utils import LineBotHandler

#執行檔案
app = Flask(__name__)

#初始化handler
linebotHandler = LineBotHandler()

# 必須放上自己的Channel Access Token
LINEBOT_API_KEY = os.getenv('LINE_BOT_API_KEY')
line_bot_api = LineBotApi(LINEBOT_API_KEY )
# 必須放上自己的Channel Secret
LINEBOT_HANDLER = os.getenv('LINE_BOT_HANDLER')
handler = WebhookHandler(LINEBOT_HANDLER)

# 監聽所有來自 /callback 的 Post Request (固定)
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
# 處理file message
@handler.add(MessageEvent, message=FileMessage)
def handle_message(event):
    # 取得使用者id
    user_id = event.source.user_id
    #把讀進來的檔案存成暫存檔
    file_message = event.message
    file_content = line_bot_api.get_message_content(file_message.id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        for chunk in file_content.iter_content():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
        
    try:
        #丟暫存檔的路徑給處理pdf的function 回傳openAI的回應
        linebotHandler.upload_pdf(temp_file_path)
        response = f"PDF file uploaded successfully:{temp_file_path}"
    except Exception as e:
        response = f"Failed to process the PDF file: {str(e)}"
    finally:
        os.remove(temp_file_path)  # 清掉暫存檔
    #傳結果訊息給使用者
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

# 處理text message
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    # 取得使用者id
    user_id = event.source.user_id
    # 讀取使用者傳來的訊息
    input_text = event.message.text 
    try:
        # 處理對話 回傳openAI的回應
        response = linebotHandler.handle_conversation(input_text)
    except Exception as e:
        response= f"Failed to text: {str(e)}"
    #傳結果訊息給使用者
    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=response))

#主程式
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)