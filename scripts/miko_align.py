"""
4 strike/standby PNG 의 캐릭터 위치 정렬.
각 프레임 발 (가장 아래쪽 opaque 행) 의 X 중심을 캔버스 가운데로 맞춰 패딩.
모든 프레임 동일 크기 → 인게임 같은 위치에 drawImage 시 캐릭터 안 흔들림.
"""
import os
import numpy as np
from PIL import Image

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\miko_taiko'
FILES = ['standby_near_normal.png', 'strike_near_normal.png',
         'standby_far_normal.png', 'strike_far_normal.png',
         'idle.png']

# 1단계: 각 프레임 측정
frames = []
for f in FILES:
    p = os.path.join(DIR, f)
    if not os.path.exists(p): continue
    arr = np.array(Image.open(p).convert('RGBA'))
    a = arr[:,:,3]
    # 가장 아래쪽 opaque 행 찾기
    rows_with_alpha = np.where((a > 50).any(axis=1))[0]
    if len(rows_with_alpha) == 0:
        print(f'SKIP {f}: no opaque'); continue
    last_row_idx = rows_with_alpha[-1]
    last_row = a[last_row_idx]
    cols_in_last = np.where(last_row > 50)[0]
    feet_x = (cols_in_last.min() + cols_in_last.max()) // 2 if len(cols_in_last) else arr.shape[1] // 2
    frames.append((f, arr, feet_x))
    print(f'{f}: size={arr.shape[1]}x{arr.shape[0]}, feet_x={feet_x}')

# 2단계: 공통 캔버스 크기 결정
# 좌측 폭 = max(feet_x), 우측 폭 = max(width - feet_x). 합이 캔버스 width.
max_left = max(fx for _, _, fx in frames)
max_right = max(arr.shape[1] - fx for _, arr, fx in frames)
new_w = max_left + max_right
new_h = max(arr.shape[0] for _, arr, _ in frames)
print(f'\n공통 캔버스: {new_w}x{new_h}, feet_x_target={max_left}')

# 3단계: 각 프레임 발 X 를 max_left 위치로 옮겨 패딩
for f, arr, feet_x in frames:
    h, w = arr.shape[:2]
    new_arr = np.zeros((new_h, new_w, 4), dtype=np.uint8)
    pad_left = max_left - feet_x  # left 패딩 크기
    pad_top = new_h - h  # 발이 바닥에 닿게 (위에서 패딩)
    new_arr[pad_top:pad_top+h, pad_left:pad_left+w] = arr
    p = os.path.join(DIR, f)
    Image.fromarray(new_arr, 'RGBA').save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p) / 1024
    print(f'{f}: padded → {new_w}x{new_h}, {sz:.0f} KB')

print('\nDone. 모든 프레임 같은 사이즈, 발 위치 동일.')
