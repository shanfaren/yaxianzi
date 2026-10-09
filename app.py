# -*- coding: utf-8 -*-
"""
牙仙子月月 - 云端后端（Render/Railway 免费托管）
环境变量：
  ARK_KEY   豆包大模型 Key（ark-开头）
  TTS_KEY   豆包语音 Key
"""
import os, json, base64, urllib.request
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

ARK_URL = "https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions"
ARK_MODEL = "doubao-seed-evolving"
TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
TTS_VOICE = "zh_female_vv_uranus_bigtts"

SYSTEM = """你是面向12岁以下儿童的护牙虚拟学伴"牙仙子月月"。Q版牙仙子，温柔甜美女声。
你只回答护牙相关话题：刷牙方法、糖与甜饮料/白开水、乳牙换牙六龄牙、看牙医情绪、常见牙齿小情况。
回答要求：温柔鼓励、短句、像跟小朋友说话；不诊断、不开药、不评价孩子牙齿好坏。
遇到牙疼/牙洞/出血/肿胀/外伤，只说："请告诉老师和家长，让牙医检查才准确。"
问到牙齿以外的事，引导回牙齿话题。不确定就说"我不确定，请老师帮助确认"，绝不编造。"""

def tts(text):
    key = os.environ.get("TTS_KEY", "")
    if not key:
        return None
    payload = json.dumps({
        "user": {"uid": "yueyue"},
        "req_params": {"text": text, "speaker": TTS_VOICE,
                       "audio_params": {"format": "mp3", "sample_rate": 24000, "speech_rate": -10}}
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
        return base64.b64encode(b"".join(chunks)).decode()
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
    q = (request.get_json() or {}).get("message", "")
    payload = json.dumps({
        "model": ARK_MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": q}],
        "temperature": 0.7, "max_tokens": 150
    }).encode()
    req = urllib.request.Request(ARK_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            ans = data["choices"][0]["message"]["content"].strip()
        return jsonify({"reply": ans, "audio": tts(ans)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/greeting.mp3")
def greeting():
    return send_from_directory(".", "greeting.mp3")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
