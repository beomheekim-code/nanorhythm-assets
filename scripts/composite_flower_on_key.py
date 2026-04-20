# -*- coding: utf-8 -*-
"""
새 꽃 sprite 를 노트키 이미지 각 셀 상단에 합성.
기존 sakura decoration 위에 덮어 그림 (alpha 블렌드) — 기존 letter/배경 보존.

팔레트 매핑:
  OLD palette idx → NEW note cell idx
  MAP[i] = i 번째 lane (OLD 팔레트) 에 그릴 새 꽃의 cell 인덱스
  rose→0, lilac→1, peach→7, coral→5, mint→3, indigo→2, cream→6, gold→4
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image

BASE = 'D:/리듬게임/skins/neon/note'
MAP = [0, 1, 7, 5, 3, 2, 6, 4]

note = Image.open(os.path.join(BASE, '벚꽃_노트.png')).convert('RGBA')
# 원본 키 복원
key  = Image.open(os.path.join(BASE, '_orig_벚꽃_노트키.png')).convert('RGBA')

KEY_COLS, KEY_ROWS = 4, 2
KEY_W, KEY_H = 688, 768
NOTE_W, NOTE_H = 352, 303

# 각 키 셀 안에서 꽃을 그릴 위치/크기
# 키 상단 약 10% 시작, 폭 55% (letter 영역 침범 방지)
FLOWER_W_RATIO = 0.55
FLOWER_TOP_RATIO = 0.12

for pal_idx in range(8):
    col = pal_idx % 4
    row = pal_idx // 4
    kx, ky = col * KEY_W, row * KEY_H

    # new flower crop
    new_cell = MAP[pal_idx]
    flower = note.crop((new_cell * NOTE_W, 0, (new_cell + 1) * NOTE_W, NOTE_H))

    # resize (aspect 유지)
    fw = int(KEY_W * FLOWER_W_RATIO)
    fh = int(fw * NOTE_H / NOTE_W)
    flower = flower.resize((fw, fh), Image.LANCZOS)

    # paste 위치 — 키 상단 중앙
    paste_x = kx + (KEY_W - fw) // 2
    paste_y = ky + int(KEY_H * FLOWER_TOP_RATIO)

    # alpha 블렌드로 기존 sakura decoration 위에 덮어 그림
    key.alpha_composite(flower, (paste_x, paste_y))
    print(f'[{pal_idx}] new_cell={new_cell}  pasted at ({paste_x},{paste_y}) size {fw}x{fh}')

key.save(os.path.join(BASE, '벚꽃_노트키.png'))
print('\nSaved 벚꽃_노트키.png')
