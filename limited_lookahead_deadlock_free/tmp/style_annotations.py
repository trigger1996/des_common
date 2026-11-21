from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '[paper]Limited Lookadhead Deadlock-free' / 'Response'
path = FOLDER / 'technical_implementation_draft.tex'
reference = FOLDER / 'technical_implementation_draft_original.tex'
reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
original = path.read_text(encoding='utf-8')


def closing_brace(value, start):
    depth = 1
    pos = start
    while depth:
        if pos >= len(value):
            raise RuntimeError('Unbalanced annotation')
        if value[pos] == '{':
            depth += 1
        elif value[pos] == '}':
            depth -= 1
        pos += 1
    return pos - 1


def strike_block(content):
    if content.lstrip().startswith(r'\If{'):
        content = content.replace(r'\If{safe-loop states are required}',
                                  r'\If{\notused{safe-loop states are required}}')
        content = re.sub(r'(Compute .*?|Set .*?)\\;',
                         lambda m: '\\notused{' + m[1].strip() + '}\\;',
                         content, flags=re.S)
        return r'\notusedblock{' + content + '}'
    parts = re.split(r'(\\\[.*?\\\])', content, flags=re.S)
    result = []
    for part in parts:
        if part.startswith(r'\['):
            result.append('\\[\n\\notusedmath{' + part[2:-2].strip() + '}\n\\]')
            continue
        for paragraph in re.split(r'(\n\s*\n)', part):
            if not paragraph.strip() or paragraph.lstrip().startswith(r'\subsection'):
                result.append(paragraph)
            else:
                lead = paragraph[:len(paragraph)-len(paragraph.lstrip())]
                tail = paragraph[len(paragraph.rstrip()):]
                result.append(lead + r'\notused{' + paragraph.strip() + '}' + tail)
    return r'\notusedblock{' + ''.join(result) + '}'


head, body = original.split(r'\begin{document}', 1)
result = []
cursor = 0
while True:
    begin = body.find(r'\notused{', cursor)
    if begin < 0:
        result.append(body[cursor:])
        break
    result.append(body[cursor:begin])
    arg_start = begin + len(r'\notused{')
    end = closing_brace(body, arg_start)
    content = body[arg_start:end]
    if '\n\n' in content or r'\[' in content or r'\If{' in content or r'\subsection' in content:
        result.append(strike_block(content))
    else:
        result.append(body[begin:end+1])
    cursor = end + 1

head = head.replace(r'\usepackage{xcolor,graphicx}',
                    '\\usepackage{xcolor,graphicx}\n\\usepackage[normalem]{ulem}\n\\usepackage{xeCJKfntef}')
old_macros = r'''\newcommand{\highlight}[1]{{\color{blue}#1}}
\newcommand{\hightlight}[1]{\highlight{#1}}
\newcommand{\comment}[1]{{\color{red}#1}}
\newcommand{\notused}[1]{{\color{gray}#1}}'''
new_macros = r'''% Muted annotation colours, with contrast ratios above 4.5:1 on white.
\definecolor{revisionblue}{HTML}{35658C}
\definecolor{commentred}{HTML}{98534A}
\definecolor{unusedgray}{HTML}{77716C}
\newcommand{\highlight}[1]{{\color{revisionblue}#1}}
\newcommand{\hightlight}[1]{\highlight{#1}}
\newcommand{\comment}[1]{{\color{commentred}#1}}
\DeclareRobustCommand{\notused}[1]{{\color{unusedgray}\CJKsout{#1}}}
% Block wrapper and display-math helper preserve paragraphs and algorithms.
\newcommand{\notusedblock}[1]{{\color{unusedgray}#1}}
\newsavebox{\unusedmathbox}
\newcommand{\notusedmath}[1]{%
  \begingroup
  \sbox{\unusedmathbox}{$\displaystyle #1$}%
  \rlap{\raisebox{0.5ex}{\rule{\wd\unusedmathbox}{0.35pt}}}%
  \usebox{\unusedmathbox}%
  \endgroup
}'''
if old_macros not in head:
    raise RuntimeError('Original annotation macros not found')
head = head.replace(old_macros, new_macros)
updated_body = ''.join(result)


def strip_wrappers(value):
    pattern = re.compile(r'\\(?:notusedblock|notusedmath|notused)\{')
    while match := pattern.search(value):
        end = closing_brace(value, match.end())
        value = value[:match.start()] + value[match.end():end] + value[end+1:]
    return re.sub(r'\s+', '', value)


if strip_wrappers(body) != strip_wrappers(updated_body):
    raise RuntimeError('Document content changed')
path.write_text(head + r'\begin{document}' + updated_body, encoding='utf-8')
if hashlib.sha256(reference.read_bytes()).hexdigest() != reference_hash:
    raise RuntimeError('Reference file changed')
print('Applied muted colours and text/math strike-through; content and reference verified unchanged.')
