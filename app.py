# -*- coding: utf-8 -*-
#載入LineBot所需要的套件
from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import tempfile
import redis
from openAI_utils import LineBotHandler
from redis_db import RedisUser
from config import LINEBOT_API_KEY, LINEBOT_HANDLER, OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, MODEL_NAME, REDIS_HOST, REDIS_PASSWORD
#執行檔案
app = Flask(__name__)

#初始化handler
linebotHandler = LineBotHandler(PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME,OPENAI_API_KEY,MODEL_NAME)
redis_user = RedisUser(host=REDIS_HOST,password=REDIS_PASSWORD)

# 必須放上自己的Channel Access Token

line_bot_api = LineBotApi(LINEBOT_API_KEY )
# 必須放上自己的Channel Secret

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
    
    match input_text:
        case "setDB":
            redis_user.set_user_name(user_id,"Zichen")
            response = TextSendMessage(text="setDB")
        case "getName":
            response = TextSendMessage(text=redis_user.get_user_name(user_id))
        case "上傳PDF":
            response = TextSendMessage(text="先將PDF檔上傳到line keep 再透過KEEP傳到聊天室")
        case "問問題":
            response = TextSendMessage(text="你有啥問題")
        case "更新google日歷":
            response = TextSendMessage("選擇服務項目",
            quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="日歷連結", text="日歷連結")),
                QuickReplyButton(action=MessageAction(label="新增日歷", text="新增日歷")),
                QuickReplyButton(action=MessageAction(label="刪除日歷", text="刪除日歷")),
                QuickReplyButton(action=MessageAction(label="查看日歷", text="查看日歷"))
            ]))
        case "更新notion":
            response = TextSendMessage("選擇服務項目",
            quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="notion連結", text="notion連結")),
                QuickReplyButton(action=MessageAction(label="新增notion", text="新增notion"))
            ]))
        case "日歷連結" | "新增日歷" | "刪除日歷" | "查看日歷" |"notion連結" | "新增notion":
            response = TextSendMessage(text="尚未完成服務")
        case _:
            try:
                # 處理對話 回傳openAI的回應
                response = TextSendMessage(text=linebotHandler.handle_conversation(input_text))
            except Exception as e:
                response= TextSendMessage(text=f"Failed to text: {str(e)}")
                
    #傳結果訊息給使用者
    line_bot_api.reply_message(event.reply_token,response)

#主程式
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)