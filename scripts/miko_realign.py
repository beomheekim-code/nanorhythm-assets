"""
miko_taiko 캐릭터 sprite 재정렬:
1. 각 파일 개별 bbox crop (빈 영역 제거)
2. 공통 height 320 으로 스케일 (비율 유지)
3. 발 위치 측정 + 공통 캔버스 너비로 패딩 (모든 프레임 발 위치 동일)
"""
import os
import numpy as np
from PIL import Image

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\miko_taiko'
FILES = ['standby_near_normal.png', 'strike_near_normal.png',
         'standby_far_normal.png', 'strike_far_normal.png',
         'standby_near_fever.png', 'strike_near_fever.png',
         'standby_far_fever.png', 'strike_far_fever.png',
         'miss.png',
         'idle.png']
TARGET_H = 320

# 1단계: 각 파일 bbox crop + scale
processed = []
for f in FILES:
    p = os.path.join(DIR, f)
    if not os.path.exists(p):
        print(f'SKIP {f}'); continue
    img = Image.open(p).convert('RGBA')
    bbox = img.getbbox()
    if not bbox:
        print(f'EMPTY {f}'); continue
    cropped = img.crop(bbox)
    cw, ch = cropped.size
    scale = TARGET_H / ch
    new_w = max(1, int(cw * scale))
    scaled = cropped.resize((new_w, TARGET_H), Image.LANCZOS)
    arr = np.array(scaled)
    # feet_x 측정
    a = arr[:,:,3]
    rows = np.where((a > 50).any(axis=1))[0]
    if len(rows) == 0: continue
    last_row = a[rows[-1]]
    cols = np.where(last_row > 50)[0]
    feet_x = (cols.min() + cols.max()) // 2 if len(cols) else new_w // 2
    processed.append((f, arr, feet_x))
    print(f'{f}: cropped {cw}x{ch} -> scaled {new_w}x{TARGET_H}, feet_x={feet_x}')

# 2단계: 공통 캔버스 (좌측 폭 + 우측 폭)
max_left = max(fx for _, _, fx in processed)
max_right = max(arr.shape[1] - fx for _, arr, fx in processed)
new_w = max_left + max_right
print(f'\n공통 캔버스: {new_w}x{TARGET_H}, feet_target={max_left}')

# 3단계: 각 프레임 발 X 정렬 + 저장
for f, arr, feet_x in processed:
    h, w = arr.shape[:2]
    canvas = np.zeros((TARGET_H, new_w, 4), dtype=np.uint8)
    pad_left = max_left - feet_x
    canvas[:h, pad_left:pad_left+w] = arr
    p = os.path.join(DIR, f)
    Image.fromarray(canvas, 'RGBA').save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p) / 1024
    print(f'{f}: {new_w}x{TARGET_H}, {sz:.0f} KB')

print('\nDone.')
