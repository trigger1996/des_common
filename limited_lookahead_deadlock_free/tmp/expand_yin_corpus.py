"""Inventory every publication entry; download and text-screen DES candidates."""
from pathlib import Path
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
import re
import urllib.request
import subprocess
import pymupdf

ROOT = Path('__ref/yin2016')
BASE = 'https://xiangyin.sjtu.edu.cn/publication.html'


def main():
    source = (ROOT/'publication_current.html').read_text(encoding='utf-8')
    rows = []
    for block in re.findall(r'<li\b[^>]*>(.*?)</li>', source, re.S | re.I):
        title = re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', ' ', block))).strip()
        urls = list(dict.fromkeys(urljoin(BASE, html.unescape(u)) for u in
                   re.findall(r'''href=["']([^"']+)["']''', block, re.I)
                   if '.pdf' in u.lower() or 'arxiv.org' in u))
        candidate = any(w in title.lower() for w in ('discrete event', 'discrete-event',
            'automata', 'automaton', 'opacity', 'observab', 'diagnos', 'prognos',
            'supervis', 'sensor activation', 'epistemic'))
        rows.append(dict(title=title, urls=urls, des_candidate=candidate))

    def fetch(url):
        catalogue_url = url
        name = Path(urlparse(url).path).name
        if not name.endswith('.pdf'):
            name = 'arxiv_' + name + '.pdf'
            url = url.replace('/abs/', '/pdf/')
        if name == '25LCSSepis.pdf':
            # Broken author-homepage link; verified coauthor-hosted copy.
            url = 'https://personal.hkust-gz.edu.cn/jiyiding/files/publications/journal/25LCSS_EpisPropDes.pdf'
        path = ROOT/name
        try:
            if not path.exists():
                try:
                    with urllib.request.urlopen(url, timeout=45) as response:
                        data = response.read()
                except urllib.error.URLError as exc:
                    if 'CERTIFICATE_VERIFY_FAILED' not in str(exc): raise
                    # Windows curl uses the OS trust store; keep TLS verification on.
                    data = subprocess.run(['curl.exe','-L','--fail','--max-time','60',url],
                                          check=True,capture_output=True).stdout
                if not data.startswith(b'%PDF'): raise ValueError('not a PDF')
                path.write_bytes(data)
            doc = pymupdf.open(path)
            texts = [page.get_text(sort=True) for page in doc]
            (ROOT/(path.stem+'.txt')).write_text('\n\f\n'.join(texts), encoding='utf-8')
            figures = [{'page':i+1,'captions':re.findall(r'(?:Fig\.|Figure)\s*\d+[^\n]*', t)}
                       for i,t in enumerate(texts) if re.search(r'(?:Fig\.|Figure)\s*\d+', t)]
            result = dict(url=url, catalogue_url=catalogue_url, path=str(path), pages=len(doc), figures=figures,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='text_screened')
            print(name, len(doc), 'pages', flush=True)
            return result
        except Exception as exc:
            print(name, type(exc).__name__, str(exc), flush=True)
            return dict(url=url, status='failed', error=str(exc))

    urls = sorted({u for r in rows if r['des_candidate'] for u in r['urls']})
    with ThreadPoolExecutor(max_workers=6) as pool:
        downloads = list(pool.map(fetch, urls))
    result = dict(catalogue_url=BASE, retrieved='2026-11-21', entries=len(rows),
                  candidates=sum(r['des_candidate'] for r in rows), publications=rows,
                  downloads=downloads,
                  scope='All listed entries inventoried; DES-title candidates text-screened. '
                        'Text screening does not certify a figure transcription or model suitability.')
    (ROOT/'expanded_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SUMMARY',len(rows),'entries;',len(urls),'candidate URLs;',
          sum(r['status']=='text_screened' for r in downloads),'PDFs screened',flush=True)


if __name__ == '__main__': main()
