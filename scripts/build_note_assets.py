# -*- coding: utf-8 -*-
"""
노트 기반 자산 일괄 빌드 — 유저가 _cells/note/ 만 갱신하면 전 노트 관련 PNG 자동 재생성.

체인:
  _cells/note/01~08.png (유저 원본)
    └─ rebuild_note_from_cells.py
         ├─ 벚꽃_노트.png (3200×400)
         └─ 벚꽃_홀드머리.png (동일 소스 복사)
    └─ generate_hold_body_from_notes.py
         └─ 벚꽃_홀드몸통.png (3200×800, 노트 색 샘플링 기반)

사용:
  python scripts/build_note_assets.py
  → 다 한번에 재생성됨.

향후 노트 디자인/색 변경 시:
  1. _cells/note/*.png 교체
  2. python scripts/build_note_assets.py
  3. (자동으로) 홀드머리/몸통 같이 갱신
  4. 게임에서 BUILD_TS 올려 캐시 부스트
"""
import sys, io, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

steps = [
    ('rebuild_note_from_cells.py', '노트 + 홀드머리 생성'),
    ('generate_hold_body_from_notes.py', '홀드몸통 생성 (노트 색 기반)'),
]

for script, desc in steps:
    path = os.path.join(SCRIPTS_DIR, script)
    print(f'\n━━━ {desc} ({script}) ━━━')
    result = subprocess.run([sys.executable, path], capture_output=False)
    if result.returncode != 0:
        print(f'❌ {script} 실패 — 중단')
        sys.exit(1)

print('\n✅ 전체 빌드 완료.')
print('   - 벚꽃_노트.png')
print('   - 벚꽃_홀드머리.png')
print('   - 벚꽃_홀드몸통.png')
print('\n다음 단계: index.html 의 __BUILD_TS 값 올려서 브라우저 캐시 부스트.')
