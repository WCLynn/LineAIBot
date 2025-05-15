from flask import Flask, request, abort, Response
import requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, StickerMessage,ImageSendMessage,
    ImageMessage, VideoMessage, LocationMessage, TextSendMessage
)
import google.generativeai as genai
import random
from dotenv import load_dotenv
import os

# load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
Gemini_API_KEY = os.getenv("Gemini_API_KEY")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
Unsplash_Acess_Key = os.getenv("Unsplash_Acess_Key")
Unsplash_Secret_Key = os.getenv("Unsplash_Secret_Key")

app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=['POST']) # 不能供人瀏覽
def callback():
    # 取得 LINE 的簽章 (header)
    signature = request.headers['X-Line-Signature']

    # 取得請求的 body 內容
    body = request.get_data(as_text=True)

    try:
        # 驗證簽章並處理訊息
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# Check API 的Response Code
def check_api(response):
    if response.status_code != 200:
        return "此功能現在無法使用，請稍後再試😖"
    return response.json()
# 紀錄API使用 API_History
def API_Record(user_id, user_text, model_text):
    if user_id not in API_History:
        API_History[user_id] = []
    API_History[user_id].append({"User": user_text, "Model":model_text})
# resuests.get
def Get_Response(url, params, headers=""):
    if headers != "":
        response = requests.get(url, headers=headers, params=params)
    else:
        response = requests.get(url, params=params)
    return check_api(response)
# Line bot 回應圖片
def Reply_img(event, img_url, text, user_id, user_text, type):
    API_Record(user_id, user_text, text)
    Reply_List = [TextSendMessage(text=text),
                    ImageSendMessage(
                        original_content_url=img_url,
                        preview_image_url=img_url
                    )
                ]
    if type == 1:
        Reply_List.append(TextSendMessage(text=f"圖片為靜態預覽圖喔😎"))
    line_bot_api.reply_message(event.reply_token, Reply_List)


genai.configure(api_key=Gemini_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash") # 初始化 Gemini 模型
user_chats = {}  # dict 裝每個人的 chat 物件
API_History = {}
"""API_History資料結構""""""
{
    "UserID1": [
        {"User": "A", "Model": "GPT-4"},
        {"User": "B", "Model": "Gemini"}
    ],
    "UserID2": [
        {"User": "C", "Model": "Claude"}
    ]
}
"""

@handler.add(MessageEvent)
def handle_all_messages(event):
    user_id = event.source.user_id
    msg = event.message
        
    # 是文字訊息，但不是 GIF: / PIC: 開頭
    is_text_and_not_special = isinstance(msg, TextMessage) and not (
        msg.text.startswith("GIF:") or msg.text.startswith("PIC:")
    )

    if is_text_and_not_special or not isinstance(msg, TextMessage):
        # 如果這 user 沒有聊天紀錄，幫他開一個
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat()
        chat = user_chats[user_id]

    # 判斷輸入訊息型態
    if isinstance(msg, TextMessage):
        user_text = msg.text
        # GIF
        if user_text.startswith("GIF:"):
            if len(user_text) < 7:
                reply = "搜尋字元不可低於3位😵‍💫"
                API_Record(user_id, user_text, reply)
            elif user_text == "GIF:Random":
                response = Get_Response("https://api.giphy.com/v1/gifs/random", {"api_key": GIPHY_API_KEY})
                if isinstance(response, str):
                    reply = response
                    API_Record(user_id, user_text, reply)
                else:    
                    gif_url = response['data']['images']['original']['url']
                    Reply_img(event, gif_url, f"GIF 來囉🎨：{gif_url}", user_id, user_text, 1)
                    return
            else:
                query = user_text[4::]
                response = Get_Response("https://api.giphy.com/v1/gifs/random", {"api_key": GIPHY_API_KEY, "tag":query})
                if isinstance(response, str):
                    reply = response
                    API_Record(user_id, user_text, reply)
                else:    
                    gif_url = response['data']['images']['original']['url']
                    Reply_img(event, gif_url, f"GIF 來囉🎨：{gif_url}", user_id, user_text, 1)
                    return  
        # PIC        
        elif user_text.startswith("PIC:"):
            if len(user_text) < 7:
                reply = "搜尋字元不可低於3位😵‍💫"
                API_Record(user_id, user_text, reply)
            elif user_text == "PIC:Random":
                response = Get_Response('https://api.unsplash.com/photos/random',{},{'Authorization': f'Client-ID {Unsplash_Acess_Key}'})

                if isinstance(response, str):
                    reply = response
                    API_Record(user_id, user_text, reply)
                else:  
                    image_url = response['urls']['regular']
                    Reply_img(event, image_url, f"PIC 來囉🎨：{image_url}", user_id, user_text, 2)
                    return
            else:
                query = user_text[4::]
                response = Get_Response('https://api.unsplash.com/search/photos', {'query': query, 'per_page': 1, 'page': random.randint(1, 10)},
                                        {'Authorization': f'Client-ID {Unsplash_Acess_Key}'})
                if isinstance(response, str):
                    reply = response
                    API_Record(user_id, user_text, reply)
                else:  
                    if len(response['results']) < 1:
                        reply = "查無圖片😖"
                        API_Record(user_id, user_text, reply)
                    else:
                        image_url = response['results'][0]['urls']['regular']
                        Reply_img(event, image_url, f"PIC 來囉🎨：{image_url}", user_id, user_text, 2)
                        return
        # 文字 (Gemini)
        else:
            reply = chat.send_message(user_text)

    elif isinstance(msg, ImageMessage):
        reply = chat.send_message("我(使用者)傳了一張圖片")
        reply = reply.text
    elif isinstance(msg, StickerMessage):
        reply = chat.send_message("我(使用者)傳了一張貼圖")
        reply = reply.text
    elif isinstance(msg, VideoMessage):
        reply = chat.send_message("我(使用者)傳了一部影片")
        reply = reply.text
    elif isinstance(msg, LocationMessage):
        reply = chat.send_message("我(使用者)傳了位置資訊")
        reply = reply.text
    else:
        reply = "這是什麼我看不懂 😵‍💫"
    if not isinstance(reply, str):
        reply = reply.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 讀取特定使用者歷史紀錄
@app.route("/history/<user_id>", methods=["GET"])
def get_history(user_id):
    Exist = False
    lines = []
    chat = user_chats.get(user_id)
    # 如果此使用者有文字紀錄就加到lines
    if chat and chat.history:
        Exist = True
        cnt = 0
        for content in chat.history:
            item = {
                "role": content.role,
                "parts": [part.text for part in content.parts]
            }
            if cnt == 0:
                lines.append("文字紀錄")
            cnt += 1
            lines.append(f'{item["role"]}: {item["parts"]}')
    # 如果此使用者有API紀錄就加到lines
    if API_History.get(user_id):
        Exist = True
        cnt = 0
        for record in API_History.get(user_id):
            if cnt == 0:
                lines.append("API使用紀錄")
            cnt += 1
            user = record.get("User")
            model = record.get("Model")
            lines.append(f'user_id: {user_id} | User: {user} | Model: {model}')
    # Response 結果    
    if not lines or not Exist:
        return Response("使用者沒有歷史紀錄!", mimetype="text/plain")
    result = "\n".join(lines)
    return Response(result, mimetype="text/plain")

# 讀取所有歷史紀錄
@app.route("/history", methods=["GET"])
def get_all_history():
    Exist = False
    lines = []
    # 如果有任一使用者文字紀錄就加到lines
    if user_chats:
        Exist = True
        cnt = 0
        for user_id, chat in user_chats.items():
            if not chat.history:
                continue
            for content in chat.history:
                item = {
                    "role": content.role,
                    "parts": [part.text for part in content.parts]
                }
                if cnt == 0:
                    lines.append("文字紀錄")
                cnt += 1
                lines.append(f'user_id: {user_id} | {item["role"]}: {item["parts"]}')
    # 如果有任一使用者API紀錄就加到lines
    if API_History:
        Exist = True
        cnt = 0        
        for user_id, records in API_History.items():
            if not records:
                continue
            for record in records:
                if cnt == 0:
                    lines.append("API使用紀錄")
                cnt += 1
                user = record.get("User")
                model = record.get("Model")
                lines.append(f'user_id: {user_id} | User: {user} | Model: {model}')
    # Response 結果
    if not lines or not Exist:
        return Response("目前沒有任何使用者的歷史紀錄!", mimetype="text/plain")

    result = "\n".join(lines)
    return Response(result, mimetype="text/plain")

# 清除特定使用者歷史紀錄
@app.route("/history/<user_id>", methods=["DELETE"])
def delete_history(user_id):
    Clr = False
    # 如果有此使用者文字紀錄就重設一個新的chat session
    if user_id in user_chats:
        user_chats[user_id] = model.start_chat()  # 重設一個新的 chat session
        Clr = True
    # 如果有此使用者API紀錄就清除
    if user_id in API_History:
        API_History[user_id].clear()
        Clr = True
    # Response 結果
    if Clr:
        return Response("歷史紀錄已清除!", mimetype="text/plain")
    else:
        return Response("沒有使用者的歷史紀錄!", mimetype="text/plain")

# 清除所有歷史紀錄
@app.route("/history", methods=["DELETE"])
def delete_all_history():
    Clr = False
    # 如果有任一使用者文字紀錄就重設一個新的chat session (each user)
    if user_chats:
        for user_id in list(user_chats.keys()):
            user_chats[user_id] = model.start_chat()
        Clr = True
    # 如果有任一使用者API紀錄就清除
    if API_History:
        API_History.clear()
        Clr = True
    # Response 結果
    if Clr:
        return Response("所有使用者的歷史紀錄都清空囉！", mimetype="text/plain")
    else:
        return Response("目前沒有任何使用者的紀錄！", mimetype="text/plain")

if __name__ == "__main__":
    app.run(port=5000)
