# -*- coding: utf-8 -*-
"""라이브러리 76곡 OGG 의 UGC fingerprint 사전 계산.
index.html 의 _ugcAudioFingerprint v2 알고리즘과 동일 구현:
  1. mono mix (stereo 평균)
  2. leading silence trim — 첫 5ms 윈도우 RMS > 0.01 인 sample
  3. 60×500ms 윈도우 RMS 계산 (firstAudio + 0.5s 부터)
  4. max-normalize
  5. 4-bit 양자화 (Math.min(15, floor(rms/maxRms * 16)))
  6. 60 byte → SHA-256 → 첫 32 hex chars

결과: lib_fingerprints.json → { hex: {name, prefix, file} }
"""
import os, sys, json, hashlib, subprocess
import numpy as np
import librosa

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def compute_fingerprint(ogg_path):
    """JS _ugcAudioFingerprint v2 동일 알고리즘."""
    y, sr = librosa.load(ogg_path, sr=None, mono=False)
    if y.ndim == 1:
        mono = y.astype(np.float64)
    else:
        # JS: (ch0[i] + ch1[i]) * 0.5
        mono = ((y[0] + y[1]) * 0.5).astype(np.float64)

    # ① Leading silence trim
    probe_win = max(1, int(sr * 0.005))
    probe_limit = min(len(mono) - probe_win, int(sr * 5))
    first_audio = 0
    for i in range(0, probe_limit, probe_win):
        seg = mono[i:i + probe_win]
        rms = np.sqrt(np.mean(seg * seg))
        if rms > 0.01:
            first_audio = i
            break

    start_sample = first_audio + int(sr * 0.5)
    win_samples = int(sr * 0.5)
    num_windows = 60

    # RMS 계산
    rms_arr = np.zeros(num_windows, dtype=np.float64)
    for w in range(num_windows):
        s0 = start_sample + w * win_samples
        s1 = min(len(mono), s0 + win_samples)
        if s0 >= len(mono):
            continue
        seg = mono[s0:s1]
        if len(seg) > 0:
            rms_arr[w] = np.sqrt(np.mean(seg * seg))

    # ② Max-normalize
    max_rms = max(float(rms_arr.max()), 0.001)

    # ③ 4-bit 양자화 (JS: Math.min(15, Math.floor((rms/maxRms) * 16)))
    norm = rms_arr / max_rms * 16
    buckets = np.minimum(15, np.floor(norm).astype(np.int64)).astype(np.uint8)

    # ④ SHA-256 → 32 hex chars
    h = hashlib.sha256(buckets.tobytes()).hexdigest()[:32]
    return h, float(max_rms), first_audio / sr, buckets.tolist()


def read_songs():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i = src.index('const songs = [')
    j = src.index('\n];', i) + 3
    arr = src[i:j].replace('const songs', 'var songs', 1)
    arr += ('\nconsole.log(JSON.stringify(songs.map(function(s){return '
            '{name:s.name,file:s.file,stemPrefix:s.stemPrefix};})));')
    tmp = os.path.join(ROOT, 'scripts', '_emit_lib_fp.js')
    open(tmp, 'w', encoding='utf-8').write(arr)
    r = subprocess.run(['node', tmp], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    os.remove(tmp)
    if r.returncode != 0:
        print('songs 추출 실패:', r.stderr[-400:])
        sys.exit(1)
    return json.loads(r.stdout)


if __name__ == '__main__':
    songs = read_songs()
    print(f'라이브러리 곡: {len(songs)} 개')
    fps = {}
    fails = 0
    for s in songs:
        if not s.get('file'):
            continue
        local_path = os.path.join(ROOT, s['file'].replace('/', os.sep))
        if not os.path.exists(local_path):
            print(f'  [skip] {s["name"]}: 파일 없음')
            continue
        try:
            fp, max_rms, fa, buckets = compute_fingerprint(local_path)
            fps[fp] = {
                'name': s['name'],
                'prefix': s.get('stemPrefix') or '',
                'file': s['file'],
                # 60 buckets (0-15, 4-bit) — Hamming distance 매칭용 (MP3↔OGG fingerprint hex 다를 때)
                'b': buckets,
            }
            print(f'  {s["name"]:30s}  {fp}  rms={max_rms:.3f}  fa={fa:.3f}s')
        except Exception as e:
            fails += 1
            print(f'  [fail] {s["name"]}: {e}')
    out_path = os.path.join(ROOT, 'lib_fingerprints.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(fps, f, ensure_ascii=False, indent=1)
    print(f'\n총 {len(fps)} fingerprint, {fails} 실패 → {out_path}')
