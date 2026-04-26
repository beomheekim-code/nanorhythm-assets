"""
sakura_tree 의 trunk(아래쪽) 만 세로 stretch.
캐노피(위쪽 50%) 는 원본 비율 유지 → 꽃 부분 안 늘어나서 자연스러움.
trunk(아래쪽 50%) 만 1.5배 늘림 → 전체 이미지 25% 길어짐.

게임 코드의 _tHScale=1.25 와 동일한 시각 효과인데 캐노피 형태 보존.

진행:
1. 이미지 분할 (top 50% / bottom 50%)
2. bottom 만 1.5x vertical resize
3. 합쳐서 새 이미지 (W x H*1.25)
4. 저장 (덮어씀)
"""
import os
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')

SPLIT_RATIO = 0.5     # 0~50% = 캐노피 (그대로), 50~100% = 트렁크 (stretch)
STRETCH = 1.5          # 트렁크 stretch factor (전체 이미지 (1+SPLIT)/2 * 0.5 + 1.5*0.5 = 1.25)

for name in ['left', 'right']:
    p = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    img = Image.open(p).convert('RGBA')
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
    print(f'{name}: {W}x{H} -> {W}x{new_h} ({(new_h/H):.2f}x), {os.path.getsize(p)/1024:.0f} KB')
