"""
1) numbers_atlas: 0-9 글자 height 통일 (1만 유독 컸던 버그 수정)
   - target_h = 310 (median 기반)
   - x, '.' 은 그대로 유지 (lowercase x 는 짧은 게 정상, '.' 는 special)
2) text sprites 테두리 클린업:
   - 작은 고립 픽셀 제거 (connected component < 80px)
   - core mask dilate 후 바깥 alpha=0 (orphan 제거)
   - green spill suppression (g > max(r,b)+5 → g=max(r,b))
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, label

# ============== 1) numbers_atlas height 통일 ==============
P = r'D:\nanorhythm-assets\nanorhythm-assets\skins\neon\numbers\numbers_atlas.png'
N_CELLS = 12
CELL_W = 220
TARGET_DIGIT_H = 310  # 0-9 통일 height

img = Image.open(P).convert('RGBA')
W, H = img.size
old_cellW = W // N_CELLS
new_arr = np.zeros((H, N_CELLS * CELL_W, 4), dtype=np.uint8)

print(f'atlas: {W}x{H} -> {N_CELLS*CELL_W}x{H}')
labels = ['0','1','2','3','4','5','6','7','8','9','x','.']
for i in range(N_CELLS):
    cell = img.crop((i*old_cellW, 0, (i+1)*old_cellW, H))
    bbox = cell.getbbox()
    if not bbox:
        continue
    glyph = cell.crop(bbox)
    gw, gh = glyph.size
    if i == 11:  # '.'
        target_h = int(H * 0.18)
        scale = target_h / gh
        new_w = int(gw * scale)
        py = H - target_h - int(H * 0.05)
    elif i == 10:  # 'x' (lowercase, 짧게 유지)
        target_h = int(TARGET_DIGIT_H * 0.68)  # ≈ 210
        scale = target_h / gh
        new_w = int(gw * scale)
        py = (H - target_h) // 2 + int(target_h * 0.15)  # baseline 보정
    else:  # 0-9 통일
        target_h = TARGET_DIGIT_H
        scale = target_h / gh
        new_w = int(gw * scale)
        py = (H - target_h) // 2
    glyph_r = glyph.resize((new_w, target_h), Image.LANCZOS)
    px = i*CELL_W + (CELL_W - new_w) // 2
    new_arr[py:py+target_h, px:px+new_w] = np.array(glyph_r)
    print(f'  {labels[i]}: {gw}x{gh} -> {new_w}x{target_h}')

Image.fromarray(new_arr, 'RGBA').save(P, optimize=True, compress_level=9)
print(f'saved atlas: {os.path.getsize(P)/1024:.0f} KB\n')

# ============== 2) text sprites 테두리 클린업 ==============
DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\neon'
SPRITES = [
    'combo_text/combo_label.png',
    'judgment_text/judge_perfect.png',
    'judgment_text/judge_great.png',
    'judgment_text/judge_good.png',
    'judgment_text/judge_miss.png',
    'score_text/score_label.png',
    'score_text/max_combo_label.png',
    'fever/fever_burst.png',
]

for rel in SPRITES:
    p = os.path.join(DIR, rel)
    if not os.path.exists(p):
        print(f'SKIP: {rel}'); continue
    img = Image.open(p).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    a = arr[:,:,3].copy()

    # (a) 작은 고립 component 제거
    mask = a > 60
    lab, n = label(mask)
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    keep = sizes > 80
    keep_mask = keep[lab]
    killed_small = int((mask & ~keep_mask).sum())

    # (b) core dilation: 강한 alpha 만 core, 주변 dilate 영역 외 orphan 제거
    core = a > 180
    soft = binary_dilation(core, iterations=3)
    soft = soft | keep_mask  # 큰 component 도 보호
    orphan = (a > 0) & ~soft
    arr[orphan, 3] = 0
    killed_orphan = int(orphan.sum())

    # (c) green spill suppression
    r,g,b_ = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    spill = (g.astype(int) > np.maximum(r, b_).astype(int) + 5) & (arr[:,:,3] > 0)
    arr[:,:,1] = np.where(spill, np.maximum(r, b_), g)
    spill_count = int(spill.sum())

    Image.fromarray(arr, 'RGBA').save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p)/1024
    print(f'{rel}: small={killed_small}, orphan={killed_orphan}, spill={spill_count}, {sz:.0f} KB')
