# -*- coding: utf-8 -*-
"""각 라이브러리 곡의 audio fingerprint 미리 계산.
첫 30s RMS pattern (100ms 윈도우, 300 floats) — 같은 곡은 인코딩 무관 동일.

출력: Music/_fingerprints.json
  {
    "Rainbow_Flight": { "stemPrefix": "Rainbow_Flight", "rms": [...300 floats...], "dur": 217.3 },
    ...
  }
"""
import os, sys, json, subprocess
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')


def emit_songs():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i = src.index('const songs = [')
    j = src.index('\n];', i) + 3
    arr = src[i:j].replace('const songs', 'var songs', 1)
    arr += ('\nconsole.log(JSON.stringify(songs.filter(function(s){return s.file;})'
            '.map(function(s){return {name:s.name,stemPrefix:s.stemPrefix||null,file:s.file};})));')
    tmp = os.path.join(ROOT, 'scripts', '_emit_fp.js')
    open(tmp, 'w', encoding='utf-8').write(arr)
    r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp)
    return json.loads(r.stdout)


def compute_fingerprint(path, sr=11025, dur=30.0, win_ms=100):
    """30s 의 100ms 윈도우 RMS = 300 floats."""
    y, _sr = librosa.load(path, sr=sr, mono=True, duration=dur)
    win = int(sr * win_ms / 1000)
    n_win = int(dur * 1000 / win_ms)
    rms = np.zeros(n_win, dtype=np.float32)
    for i in range(n_win):
        s0, s1 = i * win, min((i + 1) * win, len(y))
        chunk = y[s0:s1]
        rms[i] = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
    # 정규화 (L2)
    n = float(np.linalg.norm(rms))
    if n > 0:
        rms = rms / n
    full_dur = librosa.get_duration(path=path)
    return rms.tolist(), full_dur


songs = emit_songs()
print(f'곡 {len(songs)}개 처리 중...')

fps = {}
for s in songs:
    fpath = os.path.join(ROOT, s['file'])
    if not os.path.exists(fpath):
        print(f'  [없음] {s["file"]}')
        continue
    try:
        rms, dur = compute_fingerprint(fpath)
        prefix = s['stemPrefix'] or s['name'].replace(' ', '_')
        fps[prefix] = {
            'name': s['name'],
            'stemPrefix': s['stemPrefix'],
            'file': s['file'],
            'dur': round(dur, 2),
            'rms': [round(v, 5) for v in rms],
        }
        print(f'  {s["name"][:30]:<30} dur={dur:.1f}s')
    except Exception as e:
        print(f'  [실패] {s["name"]}: {e}')

out_path = os.path.join(MUSIC, '_fingerprints.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(fps, f, ensure_ascii=False, indent=1)
print(f'\n저장: {out_path} ({len(fps)} 곡)')
