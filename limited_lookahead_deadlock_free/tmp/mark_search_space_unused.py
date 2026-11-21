"""Preserve original files; annotate superseded comparison claims, not delete."""
from pathlib import Path
import hashlib
import re

root = Path(__file__).resolve().parents[1]
folder = root / '[paper]Limited Lookadhead Deadlock-free' / 'Response'
path = folder / 'technical_implementation_draft.tex'
originals = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob('*original*') if p.is_file()}
text = path.read_text(encoding='utf-8')
(root / 'tmp' / 'technical_implementation_draft_before_certified.tex').write_text(text, encoding='utf-8')


def annotate(block):
    # The existing CJK strikeout command cannot contain a display or a paragraph.
    # Keep its existing block/math helpers, applying notused to each prose span.
    chunks = re.split(r'(\\\[.*?\\\]|\\begin\{equation\}.*?\\end\{equation\})', block,
                      flags=re.S)
    result = []
    for c in chunks:
        if c.startswith(r'\['):
            result.append('\\[\n\\notusedmath{' + c[2:-2].strip() + '}\n\\]')
        elif c.startswith(r'\begin{equation}'):
            c = c[len(r'\begin{equation}'):-len(r'\end{equation}')].strip()
            label = re.search(r'\\label\{[^}]+\}', c)
            prefix = label.group(0) if label else ''
            if label:
                c = c.replace(prefix, '')
            result.append('\\begin{equation}\n' + prefix + '\n\\notusedmath{' + c.strip()
                          + '}\n\\end{equation}')
        else:
            for paragraph in re.split(r'(\n\s*\n)', c):
                if not paragraph.strip():
                    result.append(paragraph)
                else:
                    # Keep list labels outside text strikeout groups.
                    prefix = '\\item ' if paragraph.lstrip().startswith(r'\item ') else ''
                    content = paragraph.strip()
                    if prefix:
                        content = content[len(prefix):]
                    result.append('\n' + prefix + '\\notused{' + content + '}\n')
    return '\\notusedblock{\n' + ''.join(result) + '\n}\n'


start = text.index('为比较差值，完整BTS与本方法')
end = text.index(r'\highlight{\textbf{注意：} 返修中 Algorithm 2', start)
text = text[:start] + annotate(text[start:end]) + '\n' + text[end:]
start = text.index(r'\item \textbf{Search-space reduction.}')
end = text.index(r'\end{enumerate}', start)
text = text[:start] + annotate(text[start:end]) + text[end:]
start = text.index('Retaining safe terminal decision estimates but omitting')
end = text.index(r' $\square$', start)
text = text[:start] + '\\notused{' + text[start:end] + '}' + text[end:]
old = '前两点的$\\mathcal{D}$和$N_{\\mathrm{cert}}$保留了这一削减，而第3点直接比较整体复杂度。'
text = text.replace(old, '前两点的$\\mathcal{D}$和$N_{\\mathrm{cert}}$保留了这一削减，\\notused{而第3点直接比较整体复杂度。}')
path.write_text(text, encoding='utf-8')
assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in originals.items())
print('Annotated bilingual comparisons; all original files SHA256 unchanged:', len(originals))
