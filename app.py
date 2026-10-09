# -*- coding: utf-8 -*-
"""
牙仙子月月 - 云端后端（Render/Railway 免费托管）
环境变量：
  ARK_KEY   豆包大模型 Key（ark-开头）
  TTS_KEY   豆包语音 Key
"""
import os, json, base64, urllib.request
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__, static_folder=".", static_url_path="")

ARK_URL = "https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions"
ARK_MODEL = "doubao-seed-evolving"
TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
TTS_VOICE = "zh_female_vv_uranus_bigtts"

SYSTEM = """你是"牙仙子月月"，一个温柔可爱的Q版牙仙子，用甜美女声跟5-8岁小朋友聊天。

你的知识范围是牙齿和口腔健康，请热情、主动地回答小朋友关于护牙的一切问题。

你知道这些知识，要自信地说出来：
- 刷牙：每天早晚各刷一次，每次2分钟；外面画圈、里面竖刷、咬合面来回刷；用豌豆大的儿童牙膏
- 饮食：少喝可乐、奶茶、果汁这些甜饮料，渴了喝白开水；少吃糖和黏牙的零食；吃完东西漱口
- 换牙：6岁左右开始换牙，乳牙掉了会长恒牙，别用手晃；六龄齿是新长的大牙，要好好保护
- 看牙医：半年检查一次，牙医不可怕；牙疼、牙洞、牙龈出血要告诉爸爸妈妈去看牙医
- 其他：用牙线清理牙缝；不用牙齿咬硬物（开瓶盖、咬核桃）；多吃蔬菜和粗粮对牙齿好

回答规则：
1. 像跟幼儿园小朋友说话，短句、温柔、多鼓励，每句不超过15个字
2. 不要说"我不知道"、"我不确定"，这些知识你都知道
3. 遇到真正需要看牙医的情况（牙疼、牙洞、肿胀），温柔说"这个要让牙医叔叔看看哦，快告诉爸爸妈妈"
4. 问到牙齿以外的事，轻轻引导回来："这个月月不懂哦，我们聊聊小牙齿好不好？"
5. 不诊断、不开药、不评价小朋友牙齿好不好看"""

def tts_raw(text):
    """返回mp3字节，失败返回None"""
    key = os.environ.get("TTS_KEY", "")
    if not key:
        return None
    payload = json.dumps({
        "user": {"uid": "yueyue"},
        "req_params": {"text": text, "speaker": TTS_VOICE,
                       "audio_params": {"format": "mp3", "sample_rate": 16000, "speech_rate": -10}}
    }).encode()
    req = urllib.request.Request(TTS_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "X-Api-Key": key,
                 "X-Api-Resource-Id": "seed-tts-2.0"})
    chunks = []
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            for line in r:
                line = line.strip()
                if not line: continue
                try: o = json.loads(line)
                except: continue
                if o.get("data"): chunks.append(base64.b64decode(o["data"]))
        if not chunks: return None
        return b"".join(chunks)
    except Exception as e:
        print("TTS fail:", e)
        return None

@app.route("/")
def index():
    return send_from_directory(".", "月月对话页.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    key = os.environ.get("ARK_KEY", "")
    if not key:
        return jsonify({"error": "未配置 ARK_KEY"}), 500
    body = request.get_json() or {}
    q = body.get("message", "")
    history = body.get("history", [])
    # 组装 messages：system + 最近10轮历史 + 当前问题
    msgs = [{"role": "system", "content": SYSTEM}]
    for h in history[-20:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": q})
    payload = json.dumps({
        "model": ARK_MODEL,
        "messages": msgs,
        "temperature": 0.6, "max_tokens": 80
    }).encode()
    req = urllib.request.Request(ARK_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            ans = data["choices"][0]["message"]["content"].strip()
        return jsonify({"reply": ans})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/photo", methods=["POST"])
def photo():
    """分析上传的牙齿照片"""
    key = os.environ.get("ARK_KEY", "")
    if not key:
        return jsonify({"error": "未配置 ARK_KEY"}), 500
    data = request.get_json() or {}
    img_b64 = data.get("image", "")
    if not img_b64:
        return jsonify({"error": "无图片"}), 400

    prompt = """你是牙仙子月月。请判断这张照片拍的是不是人的牙齿/口腔。
如果是牙齿：用温柔的语气说1-2句简单的观察（比如牙齿颜色、有没有明显黑斑/蛀牙迹象、牙龈是否红肿），最后一定要说"不过这只是月月远远看的，一定要告诉爸爸妈妈，让牙医认真检查才准确哦"。
如果不是牙齿（是别的东西）：温柔地说"月月只能帮小朋友看牙齿健康哦，你拍的不是牙齿，拍张开的小嘴巴给月月看看好不好？"
要求：短句、温柔、像跟小朋友说话，不超过80字，不要用医学术语。"""

    payload = json.dumps({
        "model": ARK_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_b64}}
        ]}],
        "temperature": 0.5, "max_tokens": 120
    }).encode()
    req = urllib.request.Request(ARK_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
            ans = resp["choices"][0]["message"]["content"].strip()
        return jsonify({"reply": ans})
    except Exception as e:
        return jsonify({"reply": "月月看不太清楚呢，让爸爸妈妈带你请牙医检查最准确哦"}), 200

@app.route("/api/tts")
def tts_api():
    text = request.args.get("text", "")
    if not text: return ("", 400)
    audio = tts_raw(text)
    if not audio: return ("", 500)
    return Response(audio, mimetype="audio/mpeg",
                    headers={"Cache-Control": "no-cache"})

@app.route("/greeting.mp3")
def greeting():
    return send_from_directory(".", "greeting.mp3")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
