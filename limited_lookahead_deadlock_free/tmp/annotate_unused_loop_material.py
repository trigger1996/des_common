from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '[paper]Limited Lookadhead Deadlock-free' / 'Response'
path = FOLDER / 'technical_implementation_draft.tex'
reference = FOLDER / 'technical_implementation_draft_original.tex'
reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
original = path.read_text(encoding='utf-8')
text = original


def replace_once(old, new):
    global text
    if text.count(old) != 1:
        raise RuntimeError('Expected unique text: ' + old[:100])
    text = text.replace(old, new, 1)


def wrap_between(start, end):
    global text
    begin = text.index(start)
    finish = text.index(end, begin)
    text = text[:begin] + '\\notused{\n' + text[begin:finish] + '}\n\n' + text[finish:]


replace_once(r'\newcommand{\highlight}[1]{{\color{blue}#1}}',
             r'''\newcommand{\highlight}[1]{{\color{blue}#1}}
\newcommand{\hightlight}[1]{\highlight{#1}}
\newcommand{\comment}[1]{{\color{red}#1}}
\newcommand{\notused}[1]{{\color{gray}#1}}''')

# Table cells must be annotated separately so groups do not cross '&'.
for symbol in [r'$\mathfrak{L}$', r'$Q_{\mathfrak{L}}$', r'$Q_l$']:
    match = next(line for line in text.splitlines()
                 if line.startswith(symbol + ' & '))
    left, right = match.rsplit(r'\\', 1)[0].split(' & ', 1)
    replace_once(match, r'\notused{' + left + '} & ' + r'\notused{' + right + r'}\\')

wrap_between('先定义环及其状态集合。', r'\subsection{入口状态集合 $Q_e$ 的定义}')
wrap_between(r'A loop $\mathfrak{L}$ is safe', r'\textbf{Definition.} Given a DFA $G$, let $Q_e$')
replace_once(r'因此$Q_l\subseteq Q_e$，且', r'因此\notused{$Q_l\subseteq Q_e$}，且')
wrap_between('两者的区别是：', '例如，$q_a$和$q_b$均有自环')
wrap_between('例如，$q_a$和$q_b$均有自环', '以下算法直接扫描整个状态集合$Q$')
suffix_note = 'safe-loop条件中的后缀采用$\\Sigma^*$并要求转移有定义，不限制为必须从$q_0$生成的$\\mathfrak{L}(G)$。'
replace_once(suffix_note, r'\notused{' + suffix_note + '}')
wrap_between('若还需定位safe loop，', r'\subsection{3. 搜索方向和复杂度}')
optional_item = r'\item 若需定位safe loop，用Tarjan或Kosaraju分解$G[Q_e]$，提取含环分量形成$Q_l$。'
replace_once(optional_item, r'\item \notused{' + optional_item[len(r'\item '):] + '}')
replace_once('SCC分解同样为线性时间', r'\notused{SCC分解同样为线性时间}')
replace_once('SCC分解用于进一步定位safe-loop状态，不改变$Q_e$。',
             r'\notused{SCC分解用于进一步定位safe-loop状态，不改变$Q_e$。}')
replace_once('SCC decomposition of $G[Q_e]$ identifies the safe-loop states $Q_l$.',
             r'\notused{SCC decomposition of $G[Q_e]$ identifies the safe-loop states $Q_l$.}')
wrap_between(r'\subsection{Lemma 1：有限状态下的无死锁演化与环}',
             r'\subsection{Algorithm 1：查找 $Q_f$ 和 $Q_e$}')
wrap_between(r'\If{safe-loop states are required}', r'\Return{$Q_f,Q_e$}')
replace_once('SCC为可选步骤，仅定位safe-loop状态$Q_l$，不再缩小$Q_e$。',
             r'\notused{SCC为可选步骤，仅定位safe-loop状态$Q_l$，不再缩小$Q_e$。}')


def remove_annotations(value):
    marker = '\\notused{'
    while marker in value:
        begin = value.index(marker)
        cursor = begin + len(marker)
        depth = 1
        while depth:
            if cursor >= len(value):
                raise RuntimeError('Unbalanced annotation')
            if value[cursor] == '{':
                depth += 1
            elif value[cursor] == '}':
                depth -= 1
            cursor += 1
        value = value[:begin] + value[begin+len(marker):cursor-1] + value[cursor:]
    return value


body_original = original.split(r'\begin{document}', 1)[1]
body_updated = remove_annotations(text.split(r'\begin{document}', 1)[1])
if re.sub(r'\s+', '', body_original) != re.sub(r'\s+', '', body_updated):
    raise RuntimeError('Annotation changed document content')
path.write_text(text, encoding='utf-8')
if hashlib.sha256(reference.read_bytes()).hexdigest() != reference_hash:
    raise RuntimeError('Reference file changed')
print('Added annotation commands and gray loop material; document content verified unchanged.')
