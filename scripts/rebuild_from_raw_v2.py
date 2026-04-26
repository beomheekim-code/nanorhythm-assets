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
from scipy.ndimage import distance_transform_edt, label

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

# === 3) 검은 박스 정확한 검출 (큰 connected component 만 제거) ===
# trunk 와 검은 박스 좌표 겹쳐서 강제 영역 투명은 trunk 잘림.
# 검은 박스 = 직사각형 형태의 큰 connected component (>=3000 px), trunk 의 검은 디테일 = 작은 patches (skip).
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
black_mask = (r < 60) & (g < 60) & (b < 60) & (a > 50)
black_lbl, n_black_components = label(black_mask)
sizes = np.bincount(black_lbl.ravel())
# 큰 component (>=1000 px) 만 = 박스. 작은 것은 trunk 의 그림자/디테일 → 보존.
LARGE_BLACK_THR = 1000
target = np.zeros_like(black_mask, dtype=bool)
removed = 0
for li in range(1, n_black_components + 1):
    if sizes[li] >= LARGE_BLACK_THR:
        target |= (black_lbl == li)
        removed += int(sizes[li])
arr[target, 3] = 0
print(f'  검은 박스 ({n_black_components} 컴포넌트 중 >={LARGE_BLACK_THR}px = {removed} px) 제거')

img = Image.fromarray(arr, 'RGBA')

# === 4) bbox crop ===
bbox = img.getbbox()
img = img.crop(bbox)
print(f'  bbox: {img.size}')

# (좌/우하단 강제 투명 제거 — trunk 가 우측 가장자리에 있어 강제 alpha=0 시 trunk 끝부분 잘림)

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

# === 8) 모바일 GPU 친화적으로 다운스케일 ===
# 1211x4875 = 24MB GPU 텍스처. 모바일에서 메모리 부족. 800 폭으로 줄임 (~10MB).
TARGET_W = 800
scale = TARGET_W / W
target_h = int(new_h * scale)
final = final.resize((TARGET_W, target_h), Image.LANCZOS)
print(f'  downscale: {W}x{new_h} -> {TARGET_W}x{target_h}')

# === 9) 저장 ===
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
