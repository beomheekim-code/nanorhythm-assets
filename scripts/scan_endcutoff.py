"""
모든 곡 스캔해서 endCutoff 값 계산.

알고리즘 (인게임 ambient filter 와 동일 로직):
- 0.5s 버킷, MUSICAL_STEMS = drums, bass, instrum, piano, guitar
- ABS_FLOOR = 0.02 (사람이 들리는 수준)
- 각 버킷 중 하나라도 RMS > ABS_FLOOR 이면 "musical"
- 마지막 musical 버킷을 찾음 = last_audible_sec
- endCutoff = last_audible_sec + 0.3 (판정선 도달 타이밍 여유 + 리버브 tail 약간 허용)

메인 파일 duration 대비 trail 길이도 계산해서 출력.
endCutoff 필드가 필요한 곡만 (trail >= 0.8s) 후보로 남김.
"""
import os
import json
import re
import numpy as np
import soundfile as sf

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC_DIR = os.path.join(ROOT, 'Music')
INDEX_HTML = os.path.join(ROOT, 'index.html')

BUCKET_SEC = 0.5
ABS_FLOOR = 0.02
MUSICAL_NAMES = ['drums', 'bass', 'instrum', 'piano', 'guitar']


def compute_bucket_rms(path, bucket_sec=BUCKET_SEC):
    try:
        data, sr = sf.read(path)
    except Exception as e:
        return None
    if data.ndim > 1:
        data = data.mean(axis=1)
    bs = int(sr * bucket_sec)
    nb = int(np.ceil(len(data) / bs))
    rms = np.zeros(nb, dtype=np.float32)
    for b in range(nb):
        s0 = b * bs
        s1 = min(s0 + bs, len(data))
        chunk = data[s0:s1]
        rms[b] = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
    return rms, float(len(data) / sr)


def last_musical_bucket(song_dir, prefix, file_duration):
    nb_max = 0
    stems = {}
    for name in MUSICAL_NAMES:
        p = os.path.join(song_dir, f'{prefix}_{name}.ogg')
        if not os.path.exists(p):
            continue
        res = compute_bucket_rms(p)
        if res is None:
            continue
        rms, _ = res
        stems[name] = rms
        nb_max = max(nb_max, len(rms))
    if nb_max == 0:
        return None
    last_b = -1
    for b in range(nb_max):
        for name, arr in stems.items():
            if b < len(arr) and arr[b] > ABS_FLOOR:
                last_b = b
                break
    if last_b < 0:
        return None
    # musical bucket 끝 = (last_b + 1) * BUCKET_SEC
    return (last_b + 1) * BUCKET_SEC


# songs 배열 파싱 (name, stemDir, stemPrefix, file 만)
with open(INDEX_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

start = html.index('const songs = [')
# simple scan to find end
depth = 0
i = html.index('[', start)
end = i
for j in range(i, len(html)):
    c = html[j]
    if c == '[':
        depth += 1
    elif c == ']':
        depth -= 1
        if depth == 0:
            end = j + 1
            break
songs_src = html[i:end]

# 개별 곡 블록 파싱
song_entries = []
obj_re = re.compile(r'\{[^{}]*\}', re.DOTALL)
# 간단히 중괄호 매칭해서 top-level { ... } 블록 추출
cur = 1  # skip [
brace_depth = 0
obj_start = None
for j in range(cur, len(songs_src)):
    c = songs_src[j]
    if c == '{':
        if brace_depth == 0:
            obj_start = j
        brace_depth += 1
    elif c == '}':
        brace_depth -= 1
        if brace_depth == 0 and obj_start is not None:
            song_entries.append(songs_src[obj_start:j+1])
            obj_start = None


def extract_field(block, key):
    # name: 'Foo Bar' / file: "Music/..." / bpm: 120
    # handle ' and " and numbers
    m = re.search(r"\b" + re.escape(key) + r"\s*:\s*(['\"])(.*?)\1", block, re.DOTALL)
    if m:
        return m.group(2)
    m = re.search(r"\b" + re.escape(key) + r"\s*:\s*([\d.]+)", block)
    if m:
        return m.group(1)
    return None


def has_field(block, key):
    return re.search(r"\b" + re.escape(key) + r"\s*:", block) is not None


print(f'Total songs parsed: {len(song_entries)}')
print()

results = []
for block in song_entries:
    name = extract_field(block, 'name')
    file_rel = extract_field(block, 'file')
    stem_dir = extract_field(block, 'stemDir')
    stem_prefix = extract_field(block, 'stemPrefix')
    has_cutoff = has_field(block, 'endCutoff')
    if not (name and file_rel and stem_dir and stem_prefix):
        continue
    song_dir = os.path.join(ROOT, stem_dir.replace('/', os.sep))
    file_path = os.path.join(ROOT, file_rel.replace('/', os.sep))
    if not os.path.exists(file_path):
        continue
    # 메인 파일 duration
    try:
        info = sf.info(file_path)
        file_dur = info.frames / info.samplerate
    except Exception:
        continue
    last_musical = last_musical_bucket(song_dir, stem_prefix, file_dur)
    if last_musical is None:
        results.append((name, file_dur, None, None, has_cutoff))
        continue
    trail = file_dur - last_musical
    # endCutoff = last_musical + 0.3 (약간 여유)
    cutoff = round(last_musical + 0.3, 2)
    results.append((name, file_dur, last_musical, cutoff, has_cutoff))

# 결과 출력 (trail >= 0.8s 만 후보)
print(f'{"Name":<35} {"Dur":>7} {"LastMus":>8} {"Trail":>6} {"Cutoff":>7} HasField')
print('-' * 80)
need_update = []
for name, dur, last, cut, has in results:
    if last is None:
        print(f'{name[:34]:<35} {dur:>7.1f} {"N/A":>8} {"--":>6} {"--":>7} {str(has)}')
        continue
    trail = dur - last
    marker = '***' if trail >= 0.8 else '   '
    print(f'{name[:34]:<35} {dur:>7.1f} {last:>8.1f} {trail:>6.1f} {cut:>7.1f} {str(has)} {marker}')
    if trail >= 0.8:
        need_update.append({'name': name, 'endCutoff': cut, 'has_field': has})

print()
print(f'Need endCutoff: {len(need_update)} songs (of which {sum(1 for n in need_update if n["has_field"]) } already have field)')
print()
# JSON 저장 (다음 단계에서 사용)
with open(os.path.join(ROOT, 'scripts', '_endcutoff_values.json'), 'w', encoding='utf-8') as f:
    json.dump(need_update, f, ensure_ascii=False, indent=2)
print(f'Written: scripts/_endcutoff_values.json')
