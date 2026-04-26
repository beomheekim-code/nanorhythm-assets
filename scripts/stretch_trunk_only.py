"""
sakura_tree 의 trunk(아래쪽) 만 세로 stretch.
캐노피(위쪽 32%) 는 원본 비율 유지 → 꽃/가지 안 늘어남.
trunk(아래쪽 68%) 만 stretch.

진행:
1. 검은색 픽셀 제거 (R,G,B<30 + opaque → alpha=0): 원본 trunk 그림자 → 투명.
2. 이미지 분할 (top 32% canopy / bottom 68% trunk)
3. bottom 만 stretch
4. 합쳐서 저장
"""
import os
import numpy as np
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')

SPLIT_RATIO = 0.32    # 캐노피 끝 = 원본 30% 정도 (분석 기반). 0.32 안전.
STRETCH = 1.8         # trunk stretch. 전체 이미지 (0.32 + 0.68*1.8) = 1.544x 길어짐.
BLACK_THR = 30        # R,G,B 모두 이 미만 = 검은 박스 (trunk 그림자 artifact)

for name in ['left', 'right']:
    p = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    img = Image.open(p).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    # 검은 박스 → 투명
    black = (r < BLACK_THR) & (g < BLACK_THR) & (b < BLACK_THR) & (arr[:,:,3] > 50)
    n_black = int(black.sum())
    arr[black, 3] = 0
    img = Image.fromarray(arr, 'RGBA')
    print(f'{name}: orig {w}x{h}, 검은 박스 제거 {n_black} px')

    # split + stretch
    W, H = img.size
    split_y = int(H * SPLIT_RATIO)
    top = img.crop((0, 0, W, split_y))
    bot = img.crop((0, split_y, W, H))
    new_bot_h = int((H - split_y) * STRETCH)
    bot_stretched = bot.resize((W, new_bot_h), Image.LANCZOS)
    new_h = split_y + new_bot_h
    new_img = Image.new('RGBA', (W, new_h), (0, 0, 0, 0))
    new_img.paste(top, (0, 0))
    new_img.paste(bot_stretched, (0, split_y))
    new_img.save(p, optimize=True, compress_level=9)
    print(f'  -> {W}x{new_h} ({(new_h/H):.2f}x), {os.path.getsize(p)/1024:.0f} KB')
