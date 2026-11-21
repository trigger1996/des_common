from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '[paper]Limited Lookadhead Deadlock-free' / 'Response'
BACKUP = ROOT / 'tmp' / 'latex_conversion_20261120' / 'originals'
BACKUP.mkdir(parents=True, exist_ok=True)

PREAMBLE = r'''% !TeX program = xelatex
\documentclass[UTF8,fontset=fandol,11pt,a4paper]{ctexart}
\usepackage[margin=18mm]{geometry}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{xcolor,graphicx}
\usepackage{enumitem}
\usepackage[ruled,vlined,linesnumbered,algo2e]{algorithm2e}
\usepackage[unicode,bookmarks=false,hidelinks]{hyperref}
\setlist{nosep,leftmargin=2em}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlength{\emergencystretch}{3em}
\allowdisplaybreaks
\newcommand{\highlight}[1]{{\color{blue}#1}}
\begin{document}
'''


def prepare(line):
    # Add math delimiters to existing notation, without changing its tokens.
    if line.startswith('Since q\'\' ='):
        line = line.replace("q'' = \\delta(q, s), s \\in \\Sigma_{uo}*",
                            "$q'' = \\delta(q, s), s \\in \\Sigma_{uo}*$")
        line = line.replace(r'd_{q_o}^{q_f} = \max | s |',
                            r'$d_{q_o}^{q_f} = \max | s |$')
    if line.startswith('** % '):
        line = re.sub(r"q'' \\in Q_f(?: \\cup Q_e)?", lambda m: '$' + m[0] + '$', line)
    if '给出如下例子' in line:
        line = line.replace(r'a, c \in \Sigma_uo', r'$a, c \in \Sigma_uo$')
    if '对应的子状态的集合' in line:
        line = line.replace(r'\mathcal{L}', r'$\mathcal{L}$')
    if '如果其【存在】一个后继环' in line:
        pos = line.find(r'\exists')
        if pos >= 0:
            line = line[:pos] + '$' + line[pos:] + '$'
    # Repair a missing closing brace in the source's arrow label only.
    line = line.replace(r'\xrightarrow{\sigma_{i+1} \cdots',
                        r'\xrightarrow{\sigma_{i+1}} \cdots')
    line = line.replace(r'\xrightarrow_{i+j} q_{i+j+1}',
                        r'\xrightarrow{}_{i+j} q_{i+j+1}')
    return line


def inline(text):
    saved = []

    def keep(value):
        saved.append(value)
        return f'ZZPROTECTED{len(saved)-1}ZZ'

    text = re.sub(r'\$[^$]*\$', lambda m: keep(m[0]), text)
    text = re.sub(r'\\(?:eqref|ref|cite|url)\{[^{}]*\}',
                  lambda m: keep(m[0]), text)
    text = re.sub(r'd_\{q_o\}\^\{q_f\}',
                  lambda m: keep('$' + m[0] + '$'), text)
    text = re.sub(r'(?<![A-Za-z\\])(?:Q|q)_(?:\{[^{}]*\}|[A-Za-z0-9]+)',
                  lambda m: keep('$' + m[0] + '$'), text)
    for raw, tex in [('∉', r'$\notin$'), ('∈', r'$\in$')]:
        text = text.replace(raw, keep(tex))
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    text = ''.join(replacements.get(ch, ch) for ch in text)
    text = re.sub(r'\*\*(.*?)\*\*', lambda m: r'\textbf{' + m[1] + '}', text)
    for index in range(len(saved)-1, -1, -1):
        text = text.replace(f'ZZPROTECTED{index}ZZ', saved[index])
    return text


def convert(source):
    output = [PREAMBLE]
    list_stack = []
    in_math = False
    in_code = False

    def close_lists():
        while list_stack:
            output.append(r'\end{' + list_stack.pop()[1] + '}')

    for raw in source.splitlines():
        line = prepare(raw)
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if stripped.startswith('```'):
            if not in_code:
                close_lists()
            in_code = not in_code
            continue
        if in_code:
            output.append(raw)
            continue
        if stripped == '$$':
            if not in_math and indent == 0:
                close_lists()
            output.append(r'\]' if in_math else r'\[')
            in_math = not in_math
            continue
        if in_math:
            output.append(raw.strip())
            continue
        if stripped.startswith('%'):
            output.append(raw)
            continue
        if not stripped:
            output.append('')
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if heading:
            close_lists()
            command = ['section', 'subsection', 'subsubsection', 'paragraph'][min(len(heading[1])-1, 3)]
            output.append('\\' + command + '*{' + inline(heading[2]) + '}')
            continue
        item = re.match(r'^(?:([-*])\s+|(\d+)\.\s+)(.*)', stripped)
        if item:
            env = 'itemize' if item[1] else 'enumerate'
            while list_stack and (indent < list_stack[-1][0] or
                                  (indent == list_stack[-1][0] and env != list_stack[-1][1])):
                output.append(r'\end{' + list_stack.pop()[1] + '}')
            if not list_stack or indent > list_stack[-1][0]:
                output.append(r'\begin{' + env + '}')
                list_stack.append((indent, env))
            output.append(r'\item ' + inline(item[3]))
            continue
        if list_stack and indent <= list_stack[-1][0]:
            close_lists()
        if stripped.startswith(r'\tilde{Q}_o'):
            output.extend([r'\[', stripped, r'\]'])
        else:
            converted = inline(stripped)
            if re.match(r'^q_.*-.*->', stripped):
                converted += r'\par'
            output.append(converted)
    close_lists()
    if in_math or in_code:
        raise ValueError('Unclosed source block')
    output.append(r'\end{document}')
    return '\n'.join(output) + '\n'


for name in ['technical_implementation_draft', 'story_logic']:
    path = FOLDER / (name + '.tex')
    original = path.read_text(encoding='utf-8')
    if original.startswith('% !TeX program'):
        raise RuntimeError('Already converted: ' + name)
    (BACKUP / (name + '.txt')).write_text(original, encoding='utf-8')
    path.write_text(convert(original), encoding='utf-8')
    print('Converted:', path.name)
