# -*- coding: utf-8 -*-
"""
개별 셀 PNG 을 그리드 sprite sheet 로 합치는 유틸.

폴더 구조:
  D:/리듬게임/skins/neon/note/
  └── _cells/
      ├── key_overlay/   ← 01.png ~ 08.png (팔레트 순)
      ├── hold_body/     ← 01.png ~ 08.png
      ├── key/           ← 01.png ~ 08.png
      ├── judge_line/    ← 01.png (단일)
      ├── note_hd/       ← 01.png ~ 08.png (고해상도 노트)
      └── hold_head_hd/  ← 01.png ~ 08.png

실행: python compose_sprite_sheet.py <target>
  (e.g. python compose_sprite_sheet.py key_overlay)

셀 크기가 스펙과 달라도 자동 resize (Lanczos).
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image

BASE = 'D:/리듬게임/skins/neon/note'
CELLS_DIR = os.path.join(BASE, '_cells')

# 타겟별 그리드/셀 크기 설정
CONFIGS = {
    # 8셀 가로 스트립
    'hold_body': {
        'out': '벚꽃_홀드몸통.png',
        'cols': 8, 'rows': 1,
        'cell_w': 400, 'cell_h': 800,
    },
    'note_hd': {
        'out': '벚꽃_노트.png',
        'cols': 8, 'rows': 1,
        'cell_w': 400, 'cell_h': 400,
    },
    'hold_head_hd': {
        'out': '벚꽃_홀드머리.png',
        'cols': 8, 'rows': 1,
        'cell_w': 400, 'cell_h': 400,
    },
    # 4×2 그리드 (노트키 / 오버레이)
    'key': {
        'out': '벚꽃_노트키.png',
        'cols': 4, 'rows': 2,
        'cell_w': 688, 'cell_h': 768,
    },
    'key_overlay': {
        'out': '벚꽃_노트키_오버레이.png',
        'cols': 4, 'rows': 2,
        'cell_w': 688, 'cell_h': 768,
    },
    # 단일 이미지 (판정선)
    'judge_line': {
        'out': '벚꽃_판정선.png',
        'cols': 1, 'rows': 1,
        'cell_w': 1920, 'cell_h': 128,
    },
}

def find_cells(target_name, expected_count):
    """_cells/<target>/ 서브폴더에서 번호 붙은 PNG 찾기."""
    subdir = os.path.join(CELLS_DIR, target_name)
    if not os.path.isdir(subdir):
        print(f'ERROR: 폴더가 없어: {subdir}')
        print(f'  → 만들고 거기에 01.png ~ 0{expected_count}.png 넣어.')
        sys.exit(1)
    files = sorted(glob.glob(os.path.join(subdir, '*.png')))
    if len(files) < expected_count:
        print(f'ERROR: {subdir} 에 최소 {expected_count} 개 PNG 필요. 현재 {len(files)}개.')
        sys.exit(1)
    return files[:expected_count]

def compose(target_name):
    if target_name not in CONFIGS:
        print(f'Unknown target: {target_name}')
        print(f'Available: {list(CONFIGS.keys())}')
        sys.exit(1)
    cfg = CONFIGS[target_name]
    n = cfg['cols'] * cfg['rows']
    cw, ch = cfg['cell_w'], cfg['cell_h']
    out_w, out_h = cw * cfg['cols'], ch * cfg['rows']

    cells = find_cells(target_name, n)
    canvas = Image.new('RGBA', (out_w, out_h), (0, 0, 0, 0))

    for i, path in enumerate(cells):
        col = i % cfg['cols']
        row = i // cfg['cols']
        im = Image.open(path).convert('RGBA')
        if im.size != (cw, ch):
            print(f'  cell {i+1}: {im.size} → resize to {cw}x{ch}')
            im = im.resize((cw, ch), Image.LANCZOS)
        canvas.paste(im, (col * cw, row * ch), im)
        print(f'  cell {i+1}: pasted at ({col*cw},{row*ch}) from {os.path.basename(path)}')

    out_path = os.path.join(BASE, cfg['out'])
    canvas.save(out_path)
    print(f'\n✓ {out_path}  ({out_w}x{out_h})')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python compose_sprite_sheet.py <target>')
        print(f'Targets: {list(CONFIGS.keys())}')
        sys.exit(1)
    compose(sys.argv[1])
