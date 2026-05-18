# -*- coding: utf-8 -*-
"""chart.json 의 실제 onset 밀도 기반 곡 levelBonus 자동 제안.

비교 기준 (notes/min):
  < 100  : 매우 sparse → levelBonus -0.2 (표시 레벨 하향)
  100~180: 보통 → 변경 없음
  180~250: dense → +0.2
  250~350: 매우 dense → +0.35
  > 350  : 극단 dense → +0.5
"""
import os, sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')

# index.html songs 배열 파싱 (간단 regex)
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
i = src.index('const songs = [')
j = src.index('\n];', i) + 3
arr = src[i:j].replace('const songs', 'var songs', 1)
arr += ('\nconsole.log(JSON.stringify(songs.filter(function(s){return s.stemPrefix;})'
        '.map(function(s){return {name:s.name,stemPrefix:s.stemPrefix,bpm:s.bpm,'
        'bars:s.bars,pattern:s.pattern||[],levelBonus:s.levelBonus};})));')
tmp = os.path.join(ROOT, 'scripts', '_emit_level.js')
open(tmp, 'w', encoding='utf-8').write(arr)
import subprocess
r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8', errors='replace')
os.remove(tmp)
if r.returncode != 0:
    print('songs 추출 실패')
    sys.exit(1)
songs = json.loads(r.stdout)

print(f'{"name":<28} {"bpm":>4} {"npm":>5} {"cur":>5} {"sug":>5} {"note":<6}')
print('-' * 70)
adjustments = []
for s in songs:
    cj_path = os.path.join(MUSIC, s['stemPrefix'], 'chart.json')
    if not os.path.exists(cj_path):
        continue
    try:
        cj = json.load(open(cj_path, encoding='utf-8'))
    except Exception:
        continue
    onsets = cj.get('onsets') or []
    if not onsets:
        continue
    max_t = max(o['t'] for o in onsets)
    if max_t < 5:
        continue
    notes_per_min = len(onsets) / max_t * 60
    # 제안
    if notes_per_min < 100:
        suggested = -0.2
        note = 'sparse'
    elif notes_per_min < 180:
        suggested = 0.0
        note = 'normal'
    elif notes_per_min < 250:
        suggested = 0.2
        note = 'dense'
    elif notes_per_min < 350:
        suggested = 0.35
        note = 'v.dense'
    else:
        suggested = 0.5
        note = 'extreme'
    current = s.get('levelBonus')
    cur_s = f'{current:.2f}' if current is not None else '-'
    if current is None:
        diff = abs(suggested)
    else:
        diff = abs(suggested - current)
    needs_change = diff >= 0.2
    flag = '★' if needs_change else ' '
    print(f'{s["name"][:28]:<28} {s["bpm"]:>4} {notes_per_min:>5.0f} {cur_s:>5} {suggested:>+5.2f} {note:<6} {flag}')
    if needs_change:
        adjustments.append({
            'name': s['name'], 'prefix': s['stemPrefix'],
            'current': current, 'suggested': suggested,
            'npm': notes_per_min,
        })

print(f'\n변경 필요: {len(adjustments)}곡')
