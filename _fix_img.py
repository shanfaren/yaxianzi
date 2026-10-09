# -*- coding: utf-8 -*-
import base64, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(HERE, "月月对话页.html")
img_path = os.path.join(os.path.dirname(HERE), "yueyue_poster.jpg")

with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
data_uri = "data:image/jpeg;base64," + b64

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

img_tag = '<img src="' + data_uri + '" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:20px;display:block;" alt="yueyue">'

new_html = re.sub(r'<video[^>]*>.*?</video>', img_tag, html, flags=re.DOTALL)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_html)

print("Done. Video replaced with embedded image.")
print("File size:", len(new_html))
