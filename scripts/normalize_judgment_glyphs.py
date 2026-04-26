"""
judgment_text sprite 4개 (perfect/great/good/miss) 글자 height 통일.
각 PNG 안 글자 본체 (alpha > 100) bbox 측정 → 동일 글자 height 로 scale.
글로우는 같이 scale 됨 (전체 image resize, 글자 비율 일정).
"""
import os
import numpy as np
from PIL import Image

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\neon\judgment_text'
TARGET_GLYPH_H = 180  # 글자 본체 height 통일값

for name in ['judge_perfect.png', 'judge_great.png', 'judge_good.png', 'judge_miss.png']:
    p = os.path.join(DIR, name)
    img = Image.open(p).convert('RGBA')
    arr = np.array(img)
    a = arr[:,:,3]
    strong = a > 100
    if not strong.any():
        print(f'{name}: no strong alpha — skip')
        continue
    ys, xs = np.where(strong)
    glyph_h = int(ys.max() - ys.min() + 1)
    fw, fh = img.size
    scale = TARGET_GLYPH_H / glyph_h
    new_w = int(fw * scale)
    new_h = int(fh * scale)
    img_r = img.resize((new_w, new_h), Image.LANCZOS)
    img_r.save(p, optimize=True, compress_level=9)
    print(f'{name}: glyph {glyph_h} → {TARGET_GLYPH_H}, image {fw}x{fh} → {new_w}x{new_h}, {os.path.getsize(p)/1024:.0f} KB')
