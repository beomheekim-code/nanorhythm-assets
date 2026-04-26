"""
벚꽃 UI 텍스트 sprite 일괄 처리.
- green chroma 제거
- 우하단 200x200 영역 회색 픽셀만 alpha=0 (워터마크)
- bbox crop (numbers_atlas 는 X — cell 정렬 보존)
- 다운스케일 (모바일 GPU 친화)
- quantize 없이 optimize 만 (색 손실 방지)
"""
import os
import numpy as np
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
SKIN = os.path.join(ROOT, 'skins', 'neon')

ASSETS = [
    ('combo_text/combo_label.png', 800, True),
    ('judgment_text/judge_perfect.png', 800, True),
    ('judgment_text/judge_great.png', 800, True),
    ('judgment_text/judge_good.png', 800, True),
    ('judgment_text/judge_miss.png', 800, True),
    ('score_text/score_label.png', 600, True),
    ('score_text/max_combo_label.png', 600, True),
    ('fever/fever_burst.png', 1000, True),
    ('numbers/numbers_atlas.png', 1200, False),  # bbox crop X
]

WM_BOX = 200

for rel_path, target_w, do_bbox in ASSETS:
    p = os.path.join(SKIN, rel_path)
    if not os.path.exists(p):
        print(f'SKIP (not found): {rel_path}')
        continue
    img = Image.open(p).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f'\n{rel_path}: {w}x{h}, {os.path.getsize(p)/1024:.0f} KB')

    # Green chroma — loose (이끼 잔존 방지)
    r_, g_, b_ = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    green = (g_.astype(int) > r_.astype(int) + 15) & (g_.astype(int) > b_.astype(int) + 15) & (g_ > 80)
    arr[green, 3] = 0
    print(f'  green: {int(green.sum())}')

    # 우하단 200x200 회색 픽셀 (워터마크)
    if h > WM_BOX and w > WM_BOX:
        sub = arr[h-WM_BOX:h, w-WM_BOX:w]
        sr, sg, sb = sub[:,:,0], sub[:,:,1], sub[:,:,2]
        gray = (np.abs(sr.astype(int) - sg.astype(int)) < 30) & (np.abs(sg.astype(int) - sb.astype(int)) < 30) & (sr > 100)
        sub[:,:,3][gray] = 0
        print(f'  WM gray: {int(gray.sum())}')

    img = Image.fromarray(arr, 'RGBA')

    # bbox crop (numbers_atlas 는 cell 정렬 위해 skip)
    if do_bbox:
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    # 다운스케일
    cw, ch = img.size
    if cw > target_w:
        scale = target_w / cw
        img = img.resize((target_w, max(1, int(ch * scale))), Image.LANCZOS)

    img.save(p, optimize=True, compress_level=9)
    print(f'  → {img.size}, {os.path.getsize(p)/1024:.0f} KB')
