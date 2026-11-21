from pathlib import Path
import re
import shutil

root=Path('[paper]Limited Lookadhead Deadlock-free')
path=root/'Response/technical_implementation_draft.tex'
build=Path('tmp/draft_bib_consistency_20261121')
build.mkdir(exist_ok=True)
shutil.copy2(path,build/'before.tex')
s=path.read_text(encoding='utf-8')
s=s.replace(r'\usepackage{amsmath,amssymb,mathtools}',
            r'\usepackage{amsmath,amssymb,mathtools,amsthm}'+'\n'+
            r'\newtheorem{definition}{Definition}')
start=s.index(r'\newsavebox{\unusedmathbox}')
end=s.index(r'\begin{longtable}',start)
s=s[:start]+r'\begin{document}'+'\n\n'+s[end:]
# Remove the math strike-through wrapper, preserving its mathematical content.
token=r'\notusedmath{'
while token in s:
    start=s.index(token); i=start+len(token); depth=1; j=i
    while depth:
        if s[j] in '{}':
            k=j-1
            while k>=0 and s[k]=='\\': k-=1
            escaped=(j-1-k)%2
            if not escaped: depth+=1 if s[j]=='{' else -1
        j+=1
    s=s[:start]+s[i:j-1]+s[j:]
# Keep normal BibTeX citations OUTSIDE CJKsout's argument.
s=s.replace(r'\usebox{\yincitationbox}',r'}\cite{yin2016uniform}\notused{')
s=re.sub(r'\\begin\{thebibliography\}\{1\}.*?\\end\{thebibliography\}',
         lambda _:r'\bibliographystyle{IEEEtran}'+'\n'+r'\bibliography{ref_full}',s,flags=re.S)

original=(root/'main.tex').read_text(encoding='utf-8')
match=re.search(r'\\begin\{definition\}\\label\{def:deadlock_free_consistent\}.*?'
                r'\\end\{definition\}',original,re.S)
assert match
definition=match[0].replace(r'\begin{enumerate}[(i)]',r'\begin{enumerate}[label=(\roman*)]')
definition=definition.replace('retained control choices','retained control patterns')
heading=r'\subsubsection*{Corollary 1（放在LL-BTS构建及剪枝正确性之后）}'
intro=r'''\subsubsection*{LL-BTS的无死锁性与一致性（摘自正文）}

以下沿用正文记号。$\hat{\mathbb{I}}$和$\mathbb{I}$分别表示保留的决策信息状态集合和观测信息状态集合，
$\mathcal{B}_D$和$\mathcal{B}_O$分别表示坏决策信息状态集合和坏观测信息状态集合。
$\delta_{DO}$与$\delta_{OD}$分别表示控制模式更新和可观测事件更新，$!$表示相应转移有定义。

'''
assert heading in s
s=s.replace(heading,intro+definition+'\n\n'+heading,1)
old=(r'Every retained decision state has a retained control pattern, and every possible '
     r'enabled observation has a retained successor decision state, computed from the '
     r'complete unobservable reach by $\operatorname{NX}$.')
new=(r'The LL-BTS satisfies the consistency conditions of Definition~'
     r'\ref{def:deadlock_free_consistent}, with complete observable successor states '
     r'computed by $\operatorname{NX}$.')
if old in s:
    s=s.replace(old,new,1)
else:
    assert r'Definition\textasciitilde{}\ref{def:deadlock_free_consistent}' in s
    s=s.replace(r'Definition\textasciitilde{}\ref{def:deadlock_free_consistent}',
                r'Definition~\ref{def:deadlock_free_consistent}',1)
assert not any(t in s for t in ('yincitationbox','notusedmath','thebibliography'))
path.write_text(s,encoding='utf-8')
shutil.copy2(path,build/path.name)
shutil.copy2(root/'ref_full.bib',build/'ref_full.bib')
print('Updated',path,'and staged clean BibTeX build in',build)
