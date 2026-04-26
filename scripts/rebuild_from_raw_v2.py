"""
sakura_tree 재처리 — raw Gemini 원본에서 canopy 디테일 보존 + trunk 만 stretch.

이전 처리:
- inpaint 가 canopy 의 작은 hole 까지 채워 디테일 손상
- 검은 박스 제거 threshold 30 → 양끝 모서리에 잔존

새 처리 (이 스크립트):
1. raw 에서 시작 (Gemini_Generated_Image_sessbksessbksess.png)
2. green chroma 제거
3. 워터마크 우하단 200x200 mask
4. **검은 픽셀 hybrid threshold**:
   - 전체 영역: R,G,B<35 (보수적, trunk 색 안 잘림)
   - 모서리 (하단 양끝 250x250): R,G,B<70 (더 넓게)
5. bbox crop
6. **canopy 디테일 보존** — internal hole 채우지 않음
7. 워터마크 자리 좁게 inpaint (모서리 200x200, 거리 60px)
8. trunk stretch (split 32%, 1.8x)
9. left 저장 + right = horizontal flip + 40px shift
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
RAW = os.path.join(CONTAINER, 'Gemini_Generated_Image_sessbksessbksess.png')
DST_L = os.path.join(CONTAINER, 'sakura_tree_left.png')
DST_R = os.path.join(CONTAINER, 'sakura_tree_right.png')

SPLIT_RATIO = 0.40    # canopy + 가지 (top 40%) 그대로 보존, trunk(60%) 만 stretch
STRETCH = 1.8
BLACK_THR_GLOBAL = 35
BLACK_THR_CORNER = 70
CORNER_BOX = 250
WM_BOX = 200
WM_DIST = 60

# === 1) Load raw + green chroma ===
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h, w = arr.shape[:2]
print(f'raw: {w}x{h}')
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
green_hard = (g > 150) & (r < 120) & (b < 120)
arr[green_hard, 3] = 0
green_edge = ~green_hard & (g > r + 10) & (g > b + 10)
arr[green_edge, 1] = np.minimum(arr[green_edge, 0], arr[green_edge, 2])
print(f'  green: hard={int(green_hard.sum())}, edge={int(green_edge.sum())}')

# === 2) 워터마크 + edge artifact ===
arr[h-WM_BOX:h, w-WM_BOX:w, 3] = 0
arr[0:5, :, 3] = 0
arr[h-5:h, :, 3] = 0
arr[:, 0:5, 3] = 0
arr[:, w-5:w, 3] = 0

# === 3) 검은 픽셀 hybrid 제거 ===
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
black_global = (r < BLACK_THR_GLOBAL) & (g < BLACK_THR_GLOBAL) & (b < BLACK_THR_GLOBAL) & (a > 50)
black_corner = (r < BLACK_THR_CORNER) & (g < BLACK_THR_CORNER) & (b < BLACK_THR_CORNER) & (a > 50)
corner_mask = np.zeros_like(a, dtype=bool)
corner_mask[h-CORNER_BOX:h, 0:CORNER_BOX] = True
corner_mask[h-CORNER_BOX:h, w-CORNER_BOX:w] = True
total_black = black_global | (black_corner & corner_mask)
n_black = int(total_black.sum())
arr[total_black, 3] = 0
print(f'  검은 픽셀 제거: 전체 {int(black_global.sum())} + 모서리 {int((black_corner & corner_mask).sum())} = 총 {n_black}')

img = Image.fromarray(arr, 'RGBA')

# === 4) bbox crop ===
bbox = img.getbbox()
img = img.crop(bbox)
print(f'  bbox: {img.size}')

# === 4b) 좌/우하단 250x250 모서리 강제 투명 (raw 분석상 trunk 가운데 좁음 → 모서리에 트리 X) ===
arr_b = np.array(img)
hh_b, ww_b = arr_b.shape[:2]
HARD_CORNER = 250
n_hard_l = int((arr_b[hh_b-HARD_CORNER:hh_b, 0:HARD_CORNER, 3] > 0).sum())
n_hard_r = int((arr_b[hh_b-HARD_CORNER:hh_b, ww_b-HARD_CORNER:ww_b, 3] > 0).sum())
arr_b[hh_b-HARD_CORNER:hh_b, 0:HARD_CORNER, 3] = 0
arr_b[hh_b-HARD_CORNER:hh_b, ww_b-HARD_CORNER:ww_b, 3] = 0
img = Image.fromarray(arr_b, 'RGBA')
print(f'  강제 투명 (좌하 250x250: {n_hard_l} px, 우하 250x250: {n_hard_r} px)')

# === 5) 워터마크 자리 좁게 inpaint (모서리만) ===
arr = np.array(img)
hh, ww = arr.shape[:2]
mask = arr[:,:,3] > 50
dist, (iy, ix) = distance_transform_edt(~mask, return_distances=True, return_indices=True)
wm_region = np.zeros_like(mask, dtype=bool)
wm_region[hh-WM_BOX:hh, 0:WM_BOX] = True
wm_region[hh-WM_BOX:hh, ww-WM_BOX:ww] = True
wm_target = wm_region & ~mask & (dist <= WM_DIST)
n_wm = int(wm_target.sum())
if n_wm > 0:
    hy, hx = np.where(wm_target)
    sy, sx = iy[hy, hx], ix[hy, hx]
    arr[hy, hx, 0] = arr[sy, sx, 0]
    arr[hy, hx, 1] = arr[sy, sx, 1]
    arr[hy, hx, 2] = arr[sy, sx, 2]
    arr[hy, hx, 3] = arr[sy, sx, 3]
print(f'  WM 모서리 inpaint: {n_wm} px')

# === 6) 알파 threshold ===
arr[:,:,3] = np.where(arr[:,:,3] < 40, 0, arr[:,:,3]).astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

# === 7) trunk stretch (split 32%) ===
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

# === 8) 저장 ===
final.save(DST_L, optimize=True, compress_level=9)
print(f'\nleft: {W}x{new_h} ({(new_h/H):.2f}x), {os.path.getsize(DST_L)/1024:.0f} KB')

# right = horizontal flip + 40px vertical shift
arr_f = np.array(final)
arr_r = arr_f[:, ::-1, :].copy()
shift_y = 40
arr_r_shifted = np.zeros_like(arr_r)
arr_r_shifted[shift_y:, :, :] = arr_r[:-shift_y, :, :]
final_right = Image.fromarray(arr_r_shifted, 'RGBA')
final_right.save(DST_R, optimize=True, compress_level=9)
print(f'right: {W}x{new_h} (flipped + shifted), {os.path.getsize(DST_R)/1024:.0f} KB')
