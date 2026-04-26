"""
sakura_tree 재처리 — raw Gemini 원본 그대로 보존 + trunk 만 stretch.

처리 (최소 변경):
1. raw 로드
2. green chroma 제거
3. 워터마크 우하단 200x200 → alpha=0
4. 엣지 5px 정리 (artifact 방지)
5. bbox crop
6. canopy(top 40%) 그대로, trunk(bottom 60%) 만 1.8x stretch
7. 모바일 GPU 친화 다운스케일 (800px 폭)
8. left 저장 + right = horizontal flip + 40px shift

검은 픽셀 검출/제거 안 함 (이전 시도가 trunk 끝부분까지 잘랐음).
워터마크 inpaint 안 함 (sky 영역 침범 위험).
white inpaint 안 함 (raw canopy 디테일 보존).
"""
import os
import numpy as np
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
RAW = os.path.join(CONTAINER, 'Gemini_Generated_Image_sessbksessbksess.png')
DST_L = os.path.join(CONTAINER, 'sakura_tree_left.png')
DST_R = os.path.join(CONTAINER, 'sakura_tree_right.png')

SPLIT_RATIO = 0.40
STRETCH = 1.8
TARGET_W = 800
WM_BOX = 200

# === 1) Load raw ===
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h, w = arr.shape[:2]
print(f'raw: {w}x{h}')

# === 2) green chroma 제거 ===
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
green_hard = (g > 150) & (r < 120) & (b < 120)
arr[green_hard, 3] = 0
green_edge = ~green_hard & (g > r + 10) & (g > b + 10)
arr[green_edge, 1] = np.minimum(arr[green_edge, 0], arr[green_edge, 2])
print(f'  green: hard={int(green_hard.sum())}, edge={int(green_edge.sum())}')

# === 3) 워터마크 우하단 + 엣지 ===
arr[h-WM_BOX:h, w-WM_BOX:w, 3] = 0
arr[0:5, :, 3] = 0
arr[h-5:h, :, 3] = 0
arr[:, 0:5, 3] = 0
arr[:, w-5:w, 3] = 0

# === 4) 알파 threshold (엣지 크리스프) ===
arr[:,:,3] = np.where(arr[:,:,3] < 40, 0, arr[:,:,3]).astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

# === 5) bbox crop ===
bbox = img.getbbox()
img = img.crop(bbox)
print(f'  bbox crop: {img.size}')

# === 6) trunk stretch ===
W, H = img.size
split_y = int(H * SPLIT_RATIO)
top = img.crop((0, 0, W, split_y))
bot = img.crop((0, split_y, W, H))
new_bot_h = int((H - split_y) * STRETCH)
bot_stretched = bot.resize((W, new_bot_h), Image.LANCZOS)
new_h = split_y + new_bot_h
final = Image.new('RGBA', (W, new_h), (0, 0, 0, 0))
final.paste(top, (0, 0))
final.paste(bot_stretched, (0, split_y))
print(f'  stretched: {W}x{new_h} ({(new_h/H):.2f}x)')

# === 7) 다운스케일 ===
scale = TARGET_W / W
target_h = int(new_h * scale)
final = final.resize((TARGET_W, target_h), Image.LANCZOS)
print(f'  downscale: {TARGET_W}x{target_h}')

# === 8) 저장 ===
final.save(DST_L, optimize=True, compress_level=9)
print(f'left: {final.size}, {os.path.getsize(DST_L)/1024:.0f} KB')

# right = horizontal flip + 40px vertical shift
arr_f = np.array(final)
arr_r = arr_f[:, ::-1, :].copy()
shift_y = 40
arr_r_shifted = np.zeros_like(arr_r)
arr_r_shifted[shift_y:, :, :] = arr_r[:-shift_y, :, :]
final_right = Image.fromarray(arr_r_shifted, 'RGBA')
final_right.save(DST_R, optimize=True, compress_level=9)
print(f'right: {final_right.size} (flipped + shifted), {os.path.getsize(DST_R)/1024:.0f} KB')
