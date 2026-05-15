# -*- coding: utf-8 -*-
"""전곡 Demucs 재분리 배치 (1회성). 기존 stem 을 Demucs stem 으로 교체.

안전 설계:
  - temp 폴더에 먼저 분리 → 7개 stem 다 성공해야 stemDir 로 이동 (실패 시 기존 유지)
  - 곡별 try/except — 한 곡 실패해도 배치 계속
  - 진행률 로그 + 유의 곡(분리 실패 / 비-excludeStems 인데 무음) 리포트
  - 기존 stem 은 git tracked → 문제 시 git checkout 으로 복원
"""
import os, sys, json, subprocess, shutil, tempfile, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # cp949 콘솔 크래시 방지

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from separate_stems import separate_one, GAME_STEMS
import soundfile as sf
import numpy as np

DONE = {'Arcade_Turnabout', '봉인해제_Dragon', '잔상'}  # 이미 Demucs 적용

# 1) songs 배열 추출 (node)
src = open('index.html', encoding='utf-8').read()
i = src.index('const songs = [')
j = src.index('\n];', i) + 3
arr = src[i:j].replace('const songs', 'var songs', 1)
arr += ('\nconsole.log(JSON.stringify(songs.filter(function(s){return s.stemDir;})'
        '.map(function(s){return {file:s.file,stemDir:s.stemDir,stemPrefix:s.stemPrefix,'
        'excludeStems:s.excludeStems||[]};})));')
tmpjs = os.path.join('scripts', '_emit.js')
open(tmpjs, 'w', encoding='utf-8').write(arr)
r = subprocess.run(['node', tmpjs], capture_output=True, text=True, encoding='utf-8', errors='replace')
os.remove(tmpjs)
if r.returncode != 0:
    print('[FAIL] songs 추출:', r.stderr[-400:])
    sys.exit(1)
songs = json.loads(r.stdout)
print('stem-based 곡: %d' % len(songs))

# 2) 대상 필터
targets = []
for s in songs:
    name = os.path.splitext(os.path.basename(s['file']))[0]
    if name in DONE:
        continue
    if name != s['stemPrefix']:
        print('  [SKIP-mismatch] %s: basename != stemPrefix(%s)' % (name, s['stemPrefix']))
        continue
    if not os.path.exists(s['file']):
        print('  [SKIP-nofile] %s' % name)
        continue
    targets.append((name, s['file'], s['stemDir'].rstrip('/'), s['excludeStems']))

print('처리 대상: %d곡 (이미 적용 %d곡 제외)\n' % (len(targets), len(DONE)))

ok, fail, flags = [], [], []
t0 = time.time()
for idx, (name, src_ogg, stemdir, excl) in enumerate(targets, 1):
    el = (time.time() - t0) / 60
    print('[%d/%d] %s  (경과 %.0f분)' % (idx, len(targets), name, el))
    with tempfile.TemporaryDirectory() as tmp:
        try:
            success = separate_one(src_ogg, tmp)
        except Exception as e:
            success = False
            print('  [예외] %s' % e)
        produced = [f for f in os.listdir(tmp) if f.endswith('.ogg')] if os.path.isdir(tmp) else []
        if not success or len(produced) != 7:
            fail.append(name)
            print('  -> 실패 (stem %d개) — 기존 stem 유지' % len(produced))
            continue
        # 유의 체크: 비-excludeStems 인데 무음으로 나온 stem
        silent_active = []
        for si, st in enumerate(GAME_STEMS):
            p = os.path.join(tmp, '%s_%s.ogg' % (name, st))
            try:
                d, _sr = sf.read(p)
                if d.ndim > 1:
                    d = d.mean(axis=1)
                rms = float(np.sqrt(np.mean(d.astype(np.float64) ** 2)))
            except Exception:
                rms = -1
            if rms >= 0 and rms < 0.005 and si not in excl:
                silent_active.append(st)
        # stemDir 로 이동 (덮어쓰기)
        for f in produced:
            try:
                shutil.move(os.path.join(tmp, f), os.path.join(stemdir, f))
            except Exception as e:
                print('  [move 실패] %s: %s' % (f, e))
        ok.append(name)
        if silent_active:
            flags.append((name, silent_active))
            print('  -> 완료 (유의: %s 무음인데 excludeStems 아님)' % ', '.join(silent_active))
        else:
            print('  -> 완료')

print('\n' + '=' * 50)
print('=== 배치 완료 — 성공 %d / 실패 %d (총 %.0f분) ===' % (len(ok), len(fail), (time.time() - t0) / 60))
if fail:
    print('\n[실패 곡 — 기존 stem 그대로 유지됨]')
    for f in fail:
        print('  - %s' % f)
if flags:
    print('\n[유의 곡 — 비-excludeStems stem 이 Demucs 에서 무음으로 나옴]')
    for n, sts in flags:
        print('  - %s: %s' % (n, ', '.join(sts)))
if not fail and not flags:
    print('\n전곡 정상 처리. 유의 곡 없음.')
