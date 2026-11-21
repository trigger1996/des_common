from pathlib import Path
import pymupdf
import re

folder = Path('__ref/yin2016')
for path in sorted(folder.glob('*.pdf')):
    doc = pymupdf.open(path)
    text = '\n\f\n'.join(p.get_text(sort=True) for p in doc)
    (folder / (path.stem + '.txt')).write_text(text, encoding='utf-8')
    print('\nPAPER', path.stem, 'pages', len(doc))
    for i, p in enumerate(doc):
        text = p.get_text(sort=True)
        lines = text.splitlines()
        for j, line in enumerate(lines):
            if re.search(r'Fig(?:ure)?\.?\s*\d+[.:]', line):
                print('page', i+1, ' | '.join(lines[max(0,j-1):j+4])[:360])
                p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(
                    'tmp/pdfs/%s_p%d.png' % (path.stem, i+1))
