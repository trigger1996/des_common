from pathlib import Path
import hashlib
import json
import statistics
from collections import Counter

root=Path('.'); out=root/'outputs/certified_yin_benchmark'
load=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
papers=load('paper_results.json'); rows=load('random_results.json'); summary=load('summary.json')
inventory=json.loads((root/'__ref/yin2016/publication_inventory.json').read_text(encoding='utf-8'))
used={'16TACuniform','15ACCopac','16CDC','14IFAC','16WODESmax','17TAC-Range',
      '18TACrange','16TACNB','22TACopaque','24TACopa'}
coverage=[]
for item in inventory:
    names=[Path(u).stem for u in item['urls']]
    item['downloaded']=any((root/'__ref/yin2016'/Path(u).name).is_file() for u in item['urls'])
    item['used_for_models']=any(n in used for n in names)
    item['screening']='title/abstract-topic candidate; no claim of full-text review' if not item['downloaded'] else 'PDF figure/text screening'
    coverage.append(item)
(out/'literature_coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
sources=[]
for p in sorted((root/'__ref/yin2016').glob('*.pdf')):
    sources.append({'file':str(p),'url':'https://xiangyin.sjtu.edu.cn/Paper/'+p.name,
                    'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                    'used':p.stem in used})
(out/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
decisive=[r for r in rows if r['status']!='inconclusive']
full_total=sum(r['pre_seconds']+r['full_certificate_seconds'] for r in rows)
offline_total=sum(r['offline_seconds'] for r in rows)
paperonly=[r for r in papers if not r['name'].startswith('example')]
text=f'''实验记录：离线结构扫描 + 认证 LL-BTS

一、完成范围
1. technical_implementation_draft.tex 中中英文 search-space reduction、差值与时间改善
   推导、完整 BTS 整体复杂度对比（含解释与表格）均已作 notused 标记。
   沿用现有 notusedblock/notusedmath 处理多段及公式，文字逐段使用 notused。
   original 文件未编辑。生成的 PDF 已检查修改页，无新增溢出；原稿自带的缺失
   参考文献/跨文档引用仍保留，未替作者改写理论内容。
2. 官网目录保存 {len(inventory)} 条带 PDF 链接的记录（含目录中的重复文献条目），
   下载并筛查 {len(sources)} 篇相关论文，录入 {len(paperonly)} 个图示 DFA，来自 {len(used)} 篇论文。
   包括原系统、规格自动机、受控语言；不是 {len(paperonly)} 个相互独立的系统分布样本。
   并未声称已逐篇精读目录中的全部论文或提取了所有论文的全部图。
   20ACC1 Fig.1 与 24TACopa Fig.1 的对应图重复，保留后者。
   17AutomaticaTW 的反向自动机有多初态/非确定性，且验证例子未给控制事件划分，
   未猜测控制属性后送入 DFA 控制实验；17IFAC 展示工具和 NB-AES，不是新增 plant。
   15ACCopac 与 16TACuniform 的状态1自环不同，保留两个版本；同拓扑的子语言图
   保留其原论文的全局事件字母表，结果不作为统计独立样本汇总。
3. 每例目录包含 plant.json/plant.png、preprocessing.json、ll_bts.json/.dot/.png。
   DOT/JSON 的完整标签与边列表是精确模型；PNG 为布局预览。
   另外保存 u_sweeps.json、paper_results.csv、trajectories.json。
   根估计的最小可判定 u 通过 0..|Q|-1 扫描寻找，实际采用
   selected_u=max(draft_u,minimal_decisive_u)。扫描开销单列，不计入在线时间。
   它是逐例实验校准，不是新的全局理论阈值，也不保证与离线解同等宽松。

二、实现与正确性
des_core/certified_lookahead.py 实现：
  preprocess：全图扫描，按不同后继状态计算 Qd/Qf/Qe；将初始状态与可观测事件
  目标作为入口；对 Qf 并 Qe 回溯枚举不可观测简单路径，返回精确 draft_u。
  回溯无递归栈深度限制；预算耗尽会显式报错，绝不返回低估的 u。
  solve_certified：按完整估计合并 D，模式仅存可控部分，始终加入不可控事件；
  完整 UR/NX 不截断；若估计落入 Qe，用允许全部事件的隐式安全延续终止。
  对每个 closure 的每个具体状态检查至少一条受控后继，防止控制引入死锁。
  未认证的越界分支不能证明安全；通过悲观/乐观两次固定点区分 winning、
  losing（已证明无解）、inconclusive（当前窗口不能判定）。
  计数式反向剪枝，根模式取包含极大，不是仅取最大基数。
  CertifiedController 保存完整观测估计；在重新求解尚不能判定时继续使用此前
  已证明的后续控制。Example1 的12步轨迹中确有使用此回退，见逐步记录。
  validate_policy 枚举每个可达策略估计的全部保留模式和全部观测后继，不以一条
  成功物理轨迹替代验证。这里的保证是有限模型中的无死锁，不保证公平、任务
  完成、非阻塞、原论文的 opacity/diagnosability/range 属性。

与 draft 的关系及必须由作者处理的问题：
A. Theorem1 的 u <= bar_u 与 Corollary1 的 u >= bar_u 相反。实现使用后者。
   本次仅标记指定比较段，没有悄悄修改定理；需要作者确认公式。
B. Qf/Qe 的不可观测路径阈值只是覆盖相关目标的充分深度，不能单独保证问题
   可解、窗口内存在完整观测延续，或保持离线解的宽松程度。
   反例：0 --o--> 1, 1 --a--> 1, 1 --b--> 2；a,o,b 全可观测，b 可控，
   2 为死锁。Qf=Qe=空，draft_u=0，完整离线可解；u=0 的完整窗口证书却不足。
   u=1 可认证。测试 test_u_is_not_a_solvability_guarantee 固化了这个反例。
C. 只有 X 全含于 Qe 且启用全部事件的证书允许立即终止。Qe 中任意禁用模式
   仍可能导致死锁，不能把草稿的 “all admissible control” 字面推广为任意禁用。
D. 对完整 UR/NX 的查询可能走出窗口，费用已经计时，不能再说只查询窗口内
   状态。这是为满足 Corollary1 的完整估计条件所作的保守实现，而不是旧版
   UR intersect window 的乐观截断；计算模型及成本应在正式稿中说清。
E. 初始估计非空不等于离线最宽松。首批27个模型的筛查中已发现小窗口更保守的例子；
   现数据中的 same_maximal_patterns 字段逐例记录。若要完全恢复离线模式，
   可取覆盖全图的窗口；不据此宣称有限小 u 总能恢复它。
F. 空间中的节点个数不是完整字节存储量，还包括边、估计集合与预处理。
   长简单路径预处理有阶乘级最坏情形；不存在已验证的普遍更低最坏时间保证。
G. 原始 main_example*_partial 与 case1_product_benchmark 使用旧乐观语义，
   已明确列为历史复现接口。新的默认主入口与本次报告只调用认证版本。
   新版离线扫描要求显式完整 DFA；未把隐式大规模乘积的旧计时冒充新版结果。

三、实测（本机 Python {summary['python'].split()[0]}；seed={summary['seed']}）
论文 {len(paperonly)} 例 + 项目2例全部完成 u 扫描和图构建，所选 u 范围为
{min(r['selected_u'] for r in papers)}..{max(r['selected_u'] for r in papers)}。
论文按 deadlock-free 目标的判定：{dict(Counter(r['status'] for r in paperonly))}。
原论文部分标记终止状态无出边，在此目标下就是死锁；没有擅自添加自环。

随机样本 {len(rows)}，每例4..12状态、4事件、保留非平凡部分观测，分成 live/mixed/sparse
三个预先固定组各200例，没有事后挑选或手改样本。结果：
{json.dumps(summary['random_statuses'],ensure_ascii=False)}。
完整离线基线：{json.dumps(summary['offline_statuses'],ensure_ascii=False)}。
有 {len(rows)-len(decisive)} 例 draft_u 窗口不足，不能将它们作为同任务加速成功。
在 {len(decisive)} 个能够判定的有限窗口样本中，与完整离线的可解性无冲突；
完整窗口 + 证书版本在全部 {len(rows)} 例中与离线的初始极大模式集合一致。

公平基线：同一个 deadlock-free 目标、估计合并表示、显式控制枚举、计数式剪枝；
完整离线版本不使用 Qf/Qe 证书，也不求最长简单路径。不是殷老师各篇论文的
其他控制目标的复现，更不是拿其旧二次剪枝实现与本方法的新剪枝实现比较。

全部600例完整离线总时间：{offline_total:.6f} s。
完整窗口 + 证书的预处理和求解总时间：{full_total:.6f} s。
后二者任务和根模式均相同；这组小模型实验总时间比约 {offline_total/full_total:.2f}，
不说明理论最坏阶下降，也不能外推到大系统。
draft_u 的预处理/在线时间及 inconclusive 均在 random_results.json 原样报告。
这里只做单次新鲜求解，每例多为毫秒或更短，计时容易受解释器、顺序与调度影响；
宜将节点/边数和正确性作为本轮主要证据，不能作为稳定工业性能的结论。
内存另用 tracemalloc 对前30个预先固定样本测 Python 分配峰值，计时与内存测量
分开；不是进程 RSS 或 C 扩展全部内存。预处理存储包含在证书方案峰值里。
safe-heavy 的 live 组普遍 Qe=Q，很快就终止；报告分组，不用此组代表所有系统。

四、验证与复现
python -X utf8 certified_benchmark.py --samples 600 --seed 20261120
python -X utf8 -m unittest discover -s tests -v
本轮43项单元测试通过。新增8项包括90个独立小随机模型的全子集/全模式同步
固定点 oracle 对照、所有窗口深度的可靠性验证、状态估计不泄漏、重规划安全回退。
所有 source PDF 的 URL/SHA256 见 sources.json；目录筛查范围见 literature_coverage.json。
u_sweeps 与 CSV 均可直接复核。无未来系统/真实设备保证，也没有普遍可解性声明。
'''
(out/'report.txt').write_text(text,encoding='utf-8')
print(text)
