# -*- coding: utf-8 -*-
"""각 chart.json 의 onset 들을 게임 슬롯 필터 거쳐 실제 in-game 노트 수 계산 후
notes/sec 기반 levelBonus 자동 패치.

게임 코드 (generateNodesFromOnsets line 9572-9579) 와 동일 로직:
- 보통(0.45) noteDensity → minGap = sixteenth × 2 (8분음표 슬롯)
- slotSubdivision multiplier 곱

평가 기준 (보통 난이도 슬롯 거친 후 notes/sec):
  < 1.5     : -0.3 (sparse, 표시 레벨 ↓)
  1.5 ~ 3.0 :  0.0 (normal, 변경 없음)
  3.0 ~ 4.5 : +0.2 (dense)
  4.5 ~ 6.0 : +0.35 (v.dense)
  6.0 ~ 8.0 : +0.5 (extreme)
  > 8.0     : +0.65 (insane)
"""
import os, sys, json, subprocess, math, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')


def emit_songs():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i = src.index('const songs = [')
    j = src.index('\n];', i) + 3
    arr = src[i:j].replace('const songs', 'var songs', 1)
    arr += ('\nconsole.log(JSON.stringify(songs.filter(function(s){return s.stemPrefix;})'
            '.map(function(s){return {name:s.name,stemPrefix:s.stemPrefix,bpm:s.bpm,'
            'slotSubdivision:s.slotSubdivision||1,levelBonus:s.levelBonus};})));')
    tmp = os.path.join(ROOT, 'scripts', '_emit_lvl.js')
    open(tmp, 'w', encoding='utf-8').write(arr)
    r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp)
    if r.returncode != 0:
        print('songs 추출 실패')
        sys.exit(1)
    return json.loads(r.stdout)


def pow2_floor(x):
    return 2 ** math.floor(math.log2(max(x, 0.001)))


def simulate_slot_filter(onsets, bpm, slot_subdiv, density_for_diff=0.45):
    """게임 슬롯 필터 시뮬. density_for_diff=0.45 = 보통 난이도.
    minGap = sixteenth × (multiplier) × slotSubdivision
    """
    if not onsets:
        return 0
    sixteenth = 60.0 / bpm / 4
    if density_for_diff <= 0.5:
        mult = 4
    elif density_for_diff <= 0.8:
        mult = 2
    elif density_for_diff <= 1.0:
        mult = 1.5
    else:
        mult = 1
    min_gap = sixteenth * mult * pow2_floor(slot_subdiv)
    # 슬롯 단위로 시간 grouping → 슬롯당 1개 (가장 강한, 일단 첫 거)
    times = sorted(o['t'] for o in onsets)
    if not times:
        return 0
    start = times[0]
    end = times[-1]
    filtered = []
    slot_start = start
    idx = 0
    while slot_start < end + min_gap:
        slot_end = slot_start + min_gap
        # 슬롯 안 onset 1개 (첫 거 — energy 비교 생략, 갯수만 카운트)
        found = False
        while idx < len(times) and times[idx] < slot_end:
            if times[idx] >= slot_start and not found:
                filtered.append(times[idx])
                found = True
            idx += 1
        slot_start = slot_end
    return len(filtered)


def suggest_bonus(nps):
    """notes/sec → suggested levelBonus."""
    if nps < 1.5:
        return -0.3, 'sparse'
    if nps < 3.0:
        return 0.0, 'normal'
    if nps < 4.5:
        return 0.2, 'dense'
    if nps < 6.0:
        return 0.35, 'v.dense'
    if nps < 8.0:
        return 0.5, 'extreme'
    return 0.65, 'insane'


def main():
    songs = emit_songs()
    print(f'{"name":<28} {"bpm":>4} {"raw":>5} {"filt":>5} {"nps":>5} {"cur":>5} {"sug":>5} {"note":<7}')
    print('-' * 85)
    patches = []
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
        filt = simulate_slot_filter(onsets, s['bpm'], s.get('slotSubdivision', 1))
        nps = filt / max_t
        sug, label = suggest_bonus(nps)
        current = s.get('levelBonus')
        cur_s = f'{current:.2f}' if current is not None else '-'
        if current is None:
            diff_v = abs(sug)
        else:
            diff_v = abs(sug - current)
        needs = diff_v >= 0.15
        flag = '★' if needs else ' '
        print(f'{s["name"][:28]:<28} {s["bpm"]:>4} {len(onsets):>5} {filt:>5} {nps:>5.2f} {cur_s:>5} {sug:>+5.2f} {label:<7} {flag}')
        if needs:
            patches.append({'name': s['name'], 'prefix': s['stemPrefix'], 'current': current, 'suggested': sug, 'nps': nps})
    print(f'\n변경 필요: {len(patches)} 곡')

    # ★ simNps 패치 (모든 곡) + levelBonus 패치 (변경 필요 곡만)
    print('\n--- simNps + levelBonus 패치 적용 중 ---')
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    new_src = src
    sim_applied = 0
    bonus_applied = 0
    # 모든 곡 — simNps 패치 (raw difficulty 계산 기반)
    all_nps = {}
    for s in songs:
        cj_path = os.path.join(MUSIC, s['stemPrefix'], 'chart.json')
        if not os.path.exists(cj_path):
            continue
        try:
            cj = json.load(open(cj_path, encoding='utf-8'))
            onsets = cj.get('onsets') or []
            if not onsets:
                continue
            max_t = max(o['t'] for o in onsets)
            if max_t < 5:
                continue
            filt = simulate_slot_filter(onsets, s['bpm'], s.get('slotSubdivision', 1))
            all_nps[s['name']] = (filt / max_t, s['stemPrefix'])
        except Exception:
            continue

    patches_map = {p['name']: p for p in patches}

    for name, (nps_val, prefix) in all_nps.items():
        name_pat = re.escape(name)
        obj_pat = re.compile(
            r"\{[^{}]*name:\s*['\"]" + name_pat + r"['\"][^{}]*\}",
            re.DOTALL
        )
        m = obj_pat.search(new_src)
        if not m:
            print(f'  [매칭 실패] {name}')
            continue
        obj = m.group(0)
        new_obj = obj
        # simNps 패치 (소수점 2자리)
        nps_rounded = round(nps_val, 2)
        if 'simNps' in new_obj:
            new_obj = re.sub(
                r"simNps:\s*-?[0-9.]+",
                f"simNps: {nps_rounded}",
                new_obj
            )
        else:
            # 맨 뒤 } 직전에 삽입
            idx = new_obj.rfind('}')
            tail = new_obj[:idx].rstrip()
            sep = ',' if not tail.endswith(',') else ''
            new_obj = tail + f'{sep} simNps: {nps_rounded}\n  }}'
        # levelBonus 패치 (변경 필요한 경우만)
        if name in patches_map:
            p = patches_map[name]
            new_bonus = p['suggested']
            if 'levelBonus' in new_obj:
                new_obj = re.sub(
                    r"levelBonus:\s*-?[0-9.]+",
                    f"levelBonus: {new_bonus}",
                    new_obj
                )
            else:
                idx = new_obj.rfind('}')
                tail = new_obj[:idx].rstrip()
                sep = ',' if not tail.endswith(',') else ''
                new_obj = tail + f'{sep} levelBonus: {new_bonus}\n  }}'
            bonus_applied += 1
        if new_obj != obj:
            new_src = new_src.replace(obj, new_obj, 1)
            if 'simNps' in new_obj:
                sim_applied += 1
    with open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(new_src)
    print(f'simNps 패치: {sim_applied} 곡 / levelBonus 패치: {bonus_applied} 곡')


if __name__ == '__main__':
    main()
