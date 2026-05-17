# -*- coding: utf-8 -*-
"""각 chart.json 의 첫 0.15s 안 low-energy onset (intro 노이즈) 제거.
사용자 보고: Rainbow_Flight 첫 부분 노트가 미리 떨어짐."""
import os, sys, json, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')
EARLY = 0.15  # 첫 0.15초
ENERGY_FLOOR = 0.5  # 이 미만이면 노이즈로 판정

total_removed = 0
files_changed = 0
for path in glob.glob(os.path.join(MUSIC, '*', 'chart.json')):
    with open(path, encoding='utf-8') as f:
        chart = json.load(f)
    onsets = chart.get('onsets') or []
    new_onsets = []
    removed = 0
    for o in onsets:
        if o['t'] < EARLY and o.get('energy', 1) < ENERGY_FLOOR:
            removed += 1
            continue
        new_onsets.append(o)
    if removed > 0:
        chart['onsets'] = new_onsets
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(chart, f, ensure_ascii=False, indent=1)
        prefix = os.path.basename(os.path.dirname(path))
        print(f'  {prefix}: {removed} 개 intro noise 제거')
        total_removed += removed
        files_changed += 1

print(f'\n총: {files_changed} 곡, {total_removed} 노이즈 onset 제거')
