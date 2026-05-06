import librosa, math, numpy as np, soundfile as sf, os, sys, json
from collections import Counter

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
os.chdir(ROOT)

NEW_SONGS = [
    ('ATLANTIS', 'ATLANTIS'),
    ('Right_Now', 'Right_Now'),
    ('Switch_It_Up', 'Switch_It_Up'),
    ('달빛_과자상자', '달빛_과자상자'),
    ('이건_아직_시작이야', '이건_아직_시작이야'),
    ('흐릿한_이_밤', '흐릿한_이_밤'),
]

def detect_bpm(drum_stem_path):
    yd, sr = librosa.load(drum_stem_path, sr=22050)
    results = []
    for prior in [60, 90, 120, 150]:
        t, _ = librosa.beat.beat_track(y=yd, sr=sr, start_bpm=prior)
        results.append(int(round(float(t))))
    oe = librosa.onset.onset_strength(y=yd, sr=sr)
    tg = librosa.feature.tempo(onset_envelope=oe, sr=sr, aggregate=None)
    results.append(int(round(float(np.median(tg)))))
    cnt = Counter(results)
    top, top_count = cnt.most_common(1)[0]
    if top_count >= 3:
        return top, 'HIGH'
    for v in list(cnt.keys()):
        if cnt[v*2] + cnt[v] >= 3:
            return v*2, 'MED'
    return top, 'LOW'

def detect_exclude_stems(song_dir, prefix):
    stems = {0:'drums', 1:'bass', 2:'vocals', 3:'instrum', 4:'piano', 5:'guitar', 6:'other'}
    rms = {}
    for si, nm in stems.items():
        path = os.path.join(song_dir, f'{prefix}_{nm}.ogg')
        if not os.path.exists(path):
            rms[si] = 0; continue
        y, sr = librosa.load(path, sr=22050)
        rms[si] = float(np.sqrt(np.mean(y**2)))
    exclude = []
    for si in [0, 1, 4, 5, 6]:
        if rms[si] < 0.001:
            exclude.append(si)
    if rms[3] > 0.01 and (rms[0] < 0.01 or rms[3] > rms[0] * 2):
        exclude = sorted(set(exclude + [0, 1, 4, 5, 6]))
    return exclude, rms

def detect_end_cutoff(song_dir, prefix, file_duration):
    MUSICAL = ['drums', 'bass', 'instrum', 'piano', 'guitar']
    BUCKET = 0.5; FLOOR = 0.05
    stems = {}; nb_max = 0
    for name in MUSICAL:
        p = os.path.join(song_dir, f'{prefix}_{name}.ogg')
        if not os.path.exists(p): continue
        try:
            data, sr = sf.read(p)
        except:
            continue
        if data.ndim > 1: data = data.mean(axis=1)
        bs = int(sr * BUCKET)
        nb = int(np.ceil(len(data) / bs))
        rms = np.zeros(nb, dtype=np.float32)
        for b in range(nb):
            s0, s1 = b * bs, min((b + 1) * bs, len(data))
            chunk = data[s0:s1]
            rms[b] = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
        stems[name] = rms; nb_max = max(nb_max, nb)
    last_b = -1
    for b in range(nb_max):
        for arr in stems.values():
            if b < len(arr) and arr[b] > FLOOR:
                last_b = b; break
    if last_b < 0: return None
    last_musical = (last_b + 1) * BUCKET
    trail = file_duration - last_musical
    if trail < 0.8: return None
    return round(max(0.1, last_musical - 0.3), 2)

def has_vocal_only_region(song_dir, prefix):
    stems = ['drums', 'bass', 'vocals', 'piano', 'guitar']
    BUCKET = 0.5; FL_MUSIC = 0.015; FL_VOCAL = 0.008; MIN_RUN = 2
    bucket_rms = {}; nb = 0
    for name in stems:
        p = os.path.join(song_dir, f'{prefix}_{name}.ogg')
        if not os.path.exists(p): continue
        try:
            data, sr = sf.read(p)
        except: continue
        if data.ndim > 1: data = data.mean(axis=1)
        bs = int(sr * BUCKET)
        cur_nb = int(np.ceil(len(data) / bs))
        rms = np.zeros(cur_nb, dtype=np.float32)
        for b in range(cur_nb):
            s0, s1 = b * bs, min((b + 1) * bs, len(data))
            chunk = data[s0:s1]
            rms[b] = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
        bucket_rms[name] = rms; nb = max(nb, cur_nb)
    if 'vocals' not in bucket_rms: return False
    music_keys = ['drums', 'bass', 'piano', 'guitar']
    run = 0
    for b in range(nb):
        def g(k):
            arr = bucket_rms.get(k)
            return float(arr[b]) if arr is not None and b < len(arr) else 0.0
        musical = any(g(k) > FL_MUSIC for k in music_keys)
        vocal = g('vocals') > FL_VOCAL
        if not musical and vocal:
            run += 1
            if run >= MIN_RUN: return True
        else: run = 0
    return False

results = []
for folder, prefix in NEW_SONGS:
    song_dir = os.path.join('Music', folder)
    # main 파일은 Music/folder.ogg (Music 폴더 직속) — stem 들이 Music/folder/ 안
    main_path = os.path.join('Music', f'{prefix}.ogg')
    drum_path = os.path.join(song_dir, f'{prefix}_drums.ogg')
    if not os.path.exists(main_path):
        print(f'SKIP {folder}: main missing at {main_path}', flush=True)
        continue
    bpm, conf = detect_bpm(drum_path)
    try:
        info = sf.info(main_path)
        dur = info.frames / info.samplerate
    except:
        y, sr = librosa.load(main_path, sr=22050)
        dur = librosa.get_duration(y=y, sr=sr)
    bars = math.ceil(dur * bpm / 240)
    excl, rms = detect_exclude_stems(song_dir, prefix)
    cutoff = detect_end_cutoff(song_dir, prefix, dur)
    vocintro = has_vocal_only_region(song_dir, prefix)
    out = {
        'folder': folder, 'prefix': prefix, 'bpm': bpm, 'conf': conf,
        'dur': round(dur, 2), 'bars': bars, 'exclude': excl,
        'endCutoff': cutoff, 'vocalIntro': vocintro,
        'rms': {k: round(v, 4) for k, v in rms.items()},
    }
    print(json.dumps(out, ensure_ascii=False), flush=True)
    results.append(out)

with open(os.path.join(ROOT, 'scripts', 'new_song_analysis.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'\nDone — {len(results)} songs analyzed', flush=True)
