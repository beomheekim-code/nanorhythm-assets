"""
sakura_tree 재처리.
- left: raw 기반 (canopy raw 그대로 + trunk 만 stretch)
- right: user-edit 백업에서 복원 (사용자가 직접 나뭇가지 자른 버전 보존)

raw 처리 (left 만):
- 녹색 크로마키만 alpha=0
- 워터마크 우하단 50x50 만 alpha=0 (작게)
- canopy 그대로, trunk 만 1.8x stretch
- 800px 폭 다운스케일

right 는 versions/sakura_tree_pre_holefill_v2/sakura_tree_right.png 그대로 복사.
"""
import os
import shutil
import numpy as np
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
RAW = os.path.join(CONTAINER, 'Gemini_Generated_Image_sessbksessbksess.png')
DST_L = os.path.join(CONTAINER, 'sakura_tree_left.png')
DST_R = os.path.join(CONTAINER, 'sakura_tree_right.png')

SPLIT = 0.40
STRETCH = 1.8
TARGET_W = 800
WM = 50  # 작게 (이전 200 은 뿌리까지 잘랐음)

# 1. Load
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h, w = arr.shape[:2]
print(f'raw: {w}x{h}')

# 2. Green chroma 만 제거 (RGB 보정 X — canopy 색감 손상 방지)
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
green = (g > 150) & (r < 120) & (b < 120)
arr[green, 3] = 0
print(f'  green: {int(green.sum())}')

# 3. 워터마크 우하단 50x50 모서리만 (작게)
arr[h-WM:h, w-WM:w, 3] = 0
print(f'  워터마크 우하단 {WM}x{WM} 만 alpha=0')

img = Image.fromarray(arr, 'RGBA')

# 4. bbox crop
bbox = img.getbbox()
img = img.crop(bbox)
print(f'  bbox crop: {img.size}')

# 5. trunk 만 stretch (canopy = top 40% 그대로)
W, H = img.size
split_y = int(H * SPLIT)
top = img.crop((0, 0, W, split_y))
bot = img.crop((0, split_y, W, H))
new_bot_h = int((H - split_y) * STRETCH)
bot_stretched = bot.resize((W, new_bot_h), Image.LANCZOS)
new_h = split_y + new_bot_h
final = Image.new('RGBA', (W, new_h), (0, 0, 0, 0))
final.paste(top, (0, 0))
final.paste(bot_stretched, (0, split_y))
print(f'  stretched: {W}x{new_h}')

# 6. 다운스케일 (모바일 GPU 친화)
scale = TARGET_W / W
target_h = int(new_h * scale)
final = final.resize((TARGET_W, target_h), Image.LANCZOS)
print(f'  downscale: {TARGET_W}x{target_h}')

# 7. left 저장 (raw 기반)
final.save(DST_L, optimize=True, compress_level=9)
print(f'left: {final.size}, {os.path.getsize(DST_L)/1024:.0f} KB')

# 8. right = user-edit backup 그대로 복원 (사용자가 직접 나뭇가지 자른 버전 보존)
RIGHT_BACKUP = os.path.join(ROOT, 'versions', 'sakura_tree_pre_holefill_v2', 'sakura_tree_right.png')
shutil.copy(RIGHT_BACKUP, DST_R)
print(f'right: user-edit 백업에서 복원 ({os.path.getsize(DST_R)/1024:.0f} KB)')
