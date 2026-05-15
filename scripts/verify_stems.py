import re, os, sys, urllib.request

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
    c = f.read()

# stemDir + stemPrefix 페어 추출 (다양 quote)
pat = re.compile(r"""stemDir:\s*(["'])([^"']+)\1\s*,\s*stemPrefix:\s*(["'])([^"']+)\3""")
entries = [(m.group(2), m.group(4)) for m in pat.finditer(c)]
print(f'songs entries: {len(entries)}')

stems = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
missing_local = []
for d, p in entries:
    for s in stems:
        path = os.path.join(ROOT, d.replace('/', os.sep) + p + f'_{s}.ogg')
        if not os.path.exists(path):
            missing_local.append(d + p + f'_{s}.ogg')
print(f'\n== Missing local files ({len(missing_local)}):')
for m in missing_local[:30]:
    print('  ', m)

# jsdelivr 점검 (시간 절약 위해 main OGG path 만 또는 모든 stem 첫 5곡)
print('\n== jsdelivr drums.ogg sample check (first 10 songs):')
for d, p in entries[:10]:
    url = f'https://cdn.jsdelivr.net/gh/beomheekim-code/nanorhythm-assets@main/{d}{p}_drums.ogg'
    try:
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req, timeout=5)
        print(f'  {resp.status} {p}_drums.ogg')
    except urllib.error.HTTPError as e:
        print(f'  {e.code} {p}_drums.ogg')
    except Exception as e:
        print(f'  ERR {p}_drums.ogg {e}')
