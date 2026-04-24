"""
_endcutoff_values.json 을 읽어서
D:/nanorhythm-assets/nanorhythm-assets/index.html
D:/리듬게임/index.html
둘 다에 endCutoff 필드 삽입.

삽입 위치: 해당 곡 블록 내부 pattern: 라인 바로 위.
이미 endCutoff 필드 있으면 스킵 (멱등).
"""
import os
import json
import re

VALUES_JSON = r'D:\nanorhythm-assets\nanorhythm-assets\scripts\_endcutoff_values.json'
TARGETS = [
    r'D:\nanorhythm-assets\nanorhythm-assets\index.html',
    r'D:\리듬게임\index.html',
]

with open(VALUES_JSON, 'r', encoding='utf-8') as f:
    entries = json.load(f)

for target in TARGETS:
    with open(target, 'r', encoding='utf-8') as f:
        html = f.read()

    # songs 배열 경계 찾기
    start = html.index('const songs = [')
    bracket_start = html.index('[', start)
    depth = 0
    bracket_end = bracket_start
    for j in range(bracket_start, len(html)):
        c = html[j]
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                bracket_end = j + 1
                break
    before = html[:bracket_start]
    songs_src = html[bracket_start:bracket_end]
    after = html[bracket_end:]

    # 각 top-level { ... } 블록 수집
    blocks = []
    brace_depth = 0
    obj_start = None
    cur = 1
    for j in range(cur, len(songs_src)):
        c = songs_src[j]
        if c == '{':
            if brace_depth == 0:
                obj_start = j
            brace_depth += 1
        elif c == '}':
            brace_depth -= 1
            if brace_depth == 0 and obj_start is not None:
                blocks.append((obj_start, j + 1))
                obj_start = None

    # 블록마다 이름 파싱해서 entries 매칭
    updated = 0
    skipped = 0
    # blocks 를 뒤에서부터 처리해야 offset 유효
    for (bs, be) in reversed(blocks):
        block = songs_src[bs:be]
        m = re.search(r"\bname\s*:\s*(['\"])(.*?)\1", block, re.DOTALL)
        if not m:
            continue
        name = m.group(2)
        entry = next((e for e in entries if e['name'] == name), None)
        if entry is None:
            continue
        # 이미 endCutoff 있으면 skip (멱등)
        if re.search(r"\bendCutoff\s*:", block):
            skipped += 1
            continue
        cutoff = entry['endCutoff']
        # pattern: 라인 찾기 (들여쓰기 유지)
        pm = re.search(r"(\n[ \t]*)pattern\s*:", block)
        if pm:
            insert_at = bs + pm.start() + len(pm.group(1))
            indent = pm.group(1).lstrip('\n')
            insertion = f"endCutoff: {cutoff},\n{indent}"
        else:
            # fallback: 마지막 } 바로 앞에 삽입
            insert_at = be - 1
            insertion = f"    endCutoff: {cutoff},\n  "
        songs_src = songs_src[:insert_at] + insertion + songs_src[insert_at:]
        updated += 1

    new_html = before + songs_src + after
    if new_html != html:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(new_html)
    print(f'{target}: updated={updated}, skipped={skipped}')
