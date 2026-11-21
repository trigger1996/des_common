from pathlib import Path
from urllib.parse import urljoin
import re
import html
import json

folder = Path('__ref/yin2016')
s = (folder / 'publication.html').read_text(encoding='utf-8')
blocks = re.findall(r'<li\b[^>]*>(.*?)</li>', s, re.S | re.I)
rows = []
for b in blocks:
    urls = [urljoin('https://xiangyin.sjtu.edu.cn/publication.html', u)
            for u in re.findall(r'''href=["']([^"']+\.pdf)''', b, re.I)]
    if urls:
        rows.append({'text': re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', ' ', b))).strip(),
                     'urls': urls})
(folder / 'publication_inventory.json').write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('Publications with PDF links:', len(rows))
for r in rows:
    if any(w in r['text'].lower() for w in ('supervis', 'opacity', 'partial', 'lookahead')):
        print(' '.join(r['urls']), r['text'][:260])
