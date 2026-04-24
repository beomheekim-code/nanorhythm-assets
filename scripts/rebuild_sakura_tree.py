"""
sakura_tree 새 Gemini raw 에서 재처리.
- 기존: quantize 64/128 로 색 손실 → 하얀 얼룩
- 수정: quantize 없이 optimize 만, white threshold 낮춤 (170+ → inpaint)

left: 새 raw 에서 green 제거 + bbox crop + 워터마크 제거 + hole fill + white inpaint
right: left 를 horizontal flip + 살짝 scale 변형 (완전 대칭 피함)

raw: skins/neon/container/Gemini_Generated_Image_sessbksessbksess.png (유저 업로드)
백업: versions/sakura_tree_rebuild_v1/ (기존 left/right)
"""
import os
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
RAW = os.path.join(CONTAINER, 'Gemini_Generated_Image_sessbksessbksess.png')
DST_L = os.path.join(CONTAINER, 'sakura_tree_left.png')
DST_R = os.path.join(CONTAINER, 'sakura_tree_right.png')
BACKUP = os.path.join(ROOT, 'versions', 'sakura_tree_rebuild_v1')
os.makedirs(BACKUP, exist_ok=True)

# 기존 백업
for f in ['sakura_tree_left.png', 'sakura_tree_right.png']:
    src = os.path.join(CONTAINER, f)
    bk = os.path.join(BACKUP, f)
    if not os.path.exists(bk):
        shutil.copy(src, bk)
        print(f'backup: {bk}')

WHITE_THR = 170         # R,G,B 이 이상 + opaque = white 로 판정 → inpaint
SMALL_HOLE_MAX = 300    # 이 이하 hole 만 inpaint
TARGET_W = 1248         # 기존과 동일
TARGET_H = 3392

# ============================
# 1) Raw 로드 + 녹색 크로마키 제거
# ============================
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h0, w0 = arr.shape[:2]
print(f'raw: {w0}x{h0}')

r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
# 녹색 마스크 (hard)
green_hard = (g > 150) & (r < 120) & (b < 120)
# 녹색 엣지 (soft) — 초록 잔존
green_edge = (g > r + 10) & (g > b + 10) & ~green_hard
arr[green_hard, 3] = 0
# 엣지는 g 채널만 낮춤 (색감 보정)
arr[green_edge, 1] = np.minimum(arr[green_edge, 0], arr[green_edge, 2])
img = Image.fromarray(arr, 'RGBA')
print(f'  green chroma 제거: hard={int(green_hard.sum())}, edge={int(green_edge.sum())}')

# ============================
# 2) 워터마크 제거 — 우하단 200x200
# ============================
arr = np.array(img)
h, w = arr.shape[:2]
arr[h-200:h, w-200:w, 3] = 0
# 엣지 artifact 제거
arr[0:5, :, 3] = 0
arr[h-5:h, :, 3] = 0
arr[:, 0:5, 3] = 0
arr[:, w-5:w, 3] = 0
img = Image.fromarray(arr, 'RGBA')
print(f'  워터마크 + edge clear')

# ============================
# 3) bbox crop
# ============================
bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f'  bbox crop: {img.size}')

# ============================
# 4) 타겟 크기로 리사이즈 (기존 1248x3392 과 비율 유사하게 유지)
# ============================
cur_w, cur_h = img.size
# 기존과 거의 동일한 비율 유지
scale = min(TARGET_W / cur_w, TARGET_H / cur_h)
new_w = int(cur_w * scale)
new_h = int(cur_h * scale)
img = img.resize((new_w, new_h), Image.LANCZOS)
print(f'  resize: {img.size}')

# ============================
# 5) 내부 hole fill (<=300 px 만)
# ============================
arr = np.array(img)
a = arr[:, :, 3]
mask = a > 50
filled = binary_fill_holes(mask)
holes = filled & ~mask
lbl, n_labels = label(holes)
sizes = np.bincount(lbl.ravel())
small_mask = np.zeros_like(holes, dtype=bool)
small_count = 0
for li in range(1, n_labels + 1):
    if sizes[li] <= SMALL_HOLE_MAX:
        small_mask |= (lbl == li)
        small_count += 1
if small_mask.sum() > 0:
    _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
    hy, hx = np.where(small_mask)
    sy, sx = iy[hy, hx], ix[hy, hx]
    arr[hy, hx, 0] = arr[sy, sx, 0]
    arr[hy, hx, 1] = arr[sy, sx, 1]
    arr[hy, hx, 2] = arr[sy, sx, 2]
    arr[hy, hx, 3] = arr[sy, sx, 3]
print(f'  hole fill: {small_count} small (<=300px) out of {n_labels}')

# ============================
# 6) White inpaint — R,G,B >= 170 인 픽셀을 주변 non-white 색으로
#    단, 이미지 상단 40% (canopy 영역) 은 skip (꽃 하이라이트 유지)
# ============================
r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
a = arr[:, :, 3]
hh = arr.shape[0]
# 상단 40% 는 canopy (꽃 하이라이트 유지)
y_grid = np.arange(hh).reshape(-1, 1) * np.ones(arr.shape[1]).reshape(1, -1)
is_trunk_area = y_grid >= hh * 0.4
white = (r >= WHITE_THR) & (g >= WHITE_THR) & (b >= WHITE_THR) & (a > 50) & is_trunk_area
non_white_opaque = (a > 50) & ~((r >= WHITE_THR) & (g >= WHITE_THR) & (b >= WHITE_THR))
n_white = int(white.sum())
print(f'  trunk 영역 white (R,G,B>={WHITE_THR}): {n_white} px')
if n_white > 0 and non_white_opaque.any():
    _, (iy, ix) = distance_transform_edt(~non_white_opaque, return_indices=True)
    wy, wx = np.where(white)
    sy, sx = iy[wy, wx], ix[wy, wx]
    arr[wy, wx, 0] = arr[sy, sx, 0]
    arr[wy, wx, 1] = arr[sy, sx, 1]
    arr[wy, wx, 2] = arr[sy, sx, 2]
    # alpha 유지
print(f'  inpainted')

# 알파 threshold (엣지 크리스프)
a_new = arr[:, :, 3].astype(np.int32)
a_new = np.where(a_new < 40, 0, a_new)
arr[:, :, 3] = a_new.astype(np.uint8)

# ============================
# 7) 저장 — quantize 없이 optimize 만 (색 손실 방지)
# ============================
final_left = Image.fromarray(arr, 'RGBA')
final_left.save(DST_L, optimize=True, compress_level=9)
print(f'\nleft saved: {final_left.size}, {os.path.getsize(DST_L)/1024:.0f} KB')

# ============================
# 8) Right — left 를 horizontal flip + crop 살짝 다르게
# ============================
arr_r = arr[:, ::-1, :].copy()  # horizontal flip
# 살짝 vertical offset 으로 완전 대칭 피함
shift_y = 40  # 40 px 아래로 shift
arr_r_shifted = np.zeros_like(arr_r)
arr_r_shifted[shift_y:, :, :] = arr_r[:-shift_y, :, :]
final_right = Image.fromarray(arr_r_shifted, 'RGBA')
final_right.save(DST_R, optimize=True, compress_level=9)
print(f'right saved (flipped + shifted): {final_right.size}, {os.path.getsize(DST_R)/1024:.0f} KB')
