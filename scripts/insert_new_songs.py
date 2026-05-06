# -*- coding: utf-8 -*-
import os, sys
os.chdir(r'D:\nanorhythm-assets\nanorhythm-assets')

NEW_SONGS_CODE = r"""  {
    name: 'ATLANTIS', sub: 'OCEAN AMBIENT', bpm: 86,
    color: '#4287f5', bg1: '#050a14', bg2: '#0a1428',
    bars: 57, file: 'Music/ATLANTIS.ogg',
    cover: 'Music/ATLANTIS/ATLANTIS.png',
    stemDir: 'Music/ATLANTIS/',
    stemPrefix: 'ATLANTIS',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    excludeStems: [0, 1, 4, 5, 6],
    endCutoff: 155.7,
    pattern: [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,1,0,0],
    chordMode: true,
  },
  {
    name: 'Right Now', sub: 'DANCE POP', bpm: 144,
    color: '#ff5577', bg1: '#150510', bg2: '#20081a',
    bars: 73, file: 'Music/Right_Now.ogg',
    cover: 'Music/Right_Now/Right_Now.png',
    stemDir: 'Music/Right_Now/',
    stemPrefix: 'Right_Now',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    excludeStems: [4, 5],
    endCutoff: 120.2,
    pattern: [1,0,1,0, 1,0,1,0, 1,0,1,1, 0,1,0,1],
    vocalIntroRange: 'auto', chordMode: true,
  },
  {
    name: 'Switch It Up', sub: 'DANCE POP', bpm: 144,
    color: '#00d2ff', bg1: '#050f1a', bg2: '#08182a',
    bars: 78, file: 'Music/Switch_It_Up.ogg',
    cover: 'Music/Switch_It_Up/Switch_It_Up.png',
    stemDir: 'Music/Switch_It_Up/',
    stemPrefix: 'Switch_It_Up',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    excludeStems: [4],
    pattern: [1,0,1,1, 0,1,0,1, 1,0,1,0, 1,0,1,0],
    vocalIntroRange: 'auto', chordMode: true,
  },
  {
    name: '__DAL__', sub: 'K-EMOTION', bpm: 129,
    color: '#c4a4ff', bg1: '#100820', bg2: '#1a0e2e',
    bars: 91, file: 'Music/__DAL___.ogg',
    cover: 'Music/__DAL__/__DAL__.png',
    stemDir: 'Music/__DAL__/',
    stemPrefix: '__DAL__',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    excludeStems: [4],
    endCutoff: 165.7,
    pattern: [1,0,0,1, 1,0,1,0, 0,1,0,1, 1,0,1,0],
    vocalIntroRange: 'auto', chordMode: true,
  },
  {
    name: '__SIJAK__', sub: 'K-POP', bpm: 136,
    color: '#ff9900', bg1: '#170a05', bg2: '#25140a',
    bars: 100, file: 'Music/__SIJAK__.ogg',
    cover: 'Music/__SIJAK__/__SIJAK__.png',
    stemDir: 'Music/__SIJAK__/',
    stemPrefix: '__SIJAK__',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    endCutoff: 173.7,
    pattern: [1,0,1,0, 0,1,0,1, 1,0,1,0, 1,0,1,0],
    vocalIntroRange: 'auto', chordMode: true,
  },
  {
    name: '__BAM__', sub: 'K-BALLAD', bpm: 123,
    color: '#6b9eff', bg1: '#050d18', bg2: '#0c1828',
    bars: 79, file: 'Music/__BAM__.ogg',
    cover: 'Music/__BAM__/__BAM__.png',
    stemDir: 'Music/__BAM__/',
    stemPrefix: '__BAM__',
    stemNames: ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other'],
    endCutoff: 144.2,
    pattern: [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,1,0,0],
    vocalIntroRange: 'auto', chordMode: true,
  },
"""

# placeholder -> Korean (UTF-8 직접)
NEW_SONGS_CODE = NEW_SONGS_CODE.replace('__DAL__', '달빛 과자상자').replace('__SIJAK__', '이건 아직 시작이야').replace('__BAM__', '흐릿한 이 밤')

# file/path 의 _ 도 update
NEW_SONGS_CODE = NEW_SONGS_CODE.replace('달빛 과자상자_', '달빛_과자상자_').replace('달빛 과자상자.', '달빛_과자상자.').replace('달빛 과자상자/', '달빛_과자상자/')
# repeat for sijak/bam
for orig, replaced in [('이건 아직 시작이야', '이건_아직_시작이야'), ('흐릿한 이 밤', '흐릿한_이_밤')]:
    NEW_SONGS_CODE = NEW_SONGS_CODE.replace(orig + '_', replaced + '_').replace(orig + '.', replaced + '.').replace(orig + '/', replaced + '/')

# fix: file path 도 underscored 인데 위 logic 이 'name 이름 ' 의 단어 중간 _ 도 처리. 재-correct: stemPrefix 는 _ 버전
# 위 로직으로 stemPrefix 도 underscored 로 됨 - 의도

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

insert_at = None
for i, l in enumerate(lines):
    if i > 2300 and l.strip() == '];' and insert_at is None:
        insert_at = i
        break

print(f'inserting at line {insert_at+1}', flush=True)
new_lines = lines[:insert_at] + [NEW_SONGS_CODE] + lines[insert_at:]
with open('index.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# verify
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()
for kw in ['ATLANTIS', '달빛 과자상자', '이건 아직 시작이야', '흐릿한 이 밤']:
    cnt = content.count(kw)
    print(f'{cnt}x: {kw}', flush=True)
print('done', flush=True)
