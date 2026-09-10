# On-the-fly partial-observation DES non-deadlock：备忘录与代码修改建议

> 目的：把上传论文中的 **on-the-fly + partial observation + belief-state construction** 思想，迁移到当前代码库的纯 DES non-deadlock 分析中。本文不讨论 LTL/LTLf specification，只把论文中的 observable progression 思路抽象成 DES 的 belief / unobservable-closure / on-demand successor expansion。

---

## 0. 一句话结论

**partial observation 的运行时信息粒度应该是当前 belief state，而不是真实 plant state；on-the-fly 的实现粒度应该是“按需展开当前 belief 的局部 unobservable closure 和 observable successors”，而不是预先构造完整 observer，也不是只看一个 concrete outgoing transition。**

在当前项目中，建议把 partial-observation non-deadlock 的核心抽象固定为：

```text
current closed belief B
  -> choose/control pattern gamma, if doing synthesis
  -> local unobservable closure UR_gamma(B)
  -> classify deadlock risk over all q in UR_gamma(B)
  -> enumerate observable successors only from this local closure
  -> successor belief B' = UR_gamma'(Post(UR_gamma(B), observable_event))
```

如果只是做 analysis 而不是 supervisory synthesis，可以先令 `gamma = all events`，即不禁用任何事件。

---

## 1. 资料来源与适用边界

参考资料：

1. `On-the-fly LTLf Synthesis under Partial Observability.pdf`
   - 关键思想：partial observation 通过 belief-state DFA / subset construction 处理 hidden variables；on-the-fly 通过 observable progression 按需生成 belief states 和 transitions；MTBDD 版本通过对 unobservable variables 做 universal quantification 得到 observable successor。
   - 迁移到 DES 时，不需要保留 LTLf 公式 progression，只保留“当前观测对应多个 hidden possibilities，successor 必须合并所有 hidden completions”的结构。

2. `on the fly non deadlock.pdf`
   - 该文件是 1 页手写草图，无可解析文本层。
   - 我将其中的主要意图理解为：区分 full-observation / partial-observation、on-the-fly 探索、observer 或 belief-state construction、frontier 扩张、unobservable reach、以及 explicit / implicit / no-deadlock 判定。

3. 当前代码
   - 当前代码是 non-deadlock demo。
   - 代码已有 `DFA`、observer construction、plant-level partial-observation animation、belief-state animation 等基础，但语义层面还需要把“已发现边导致的暂时 deadlock 显示”与“DES 语义上的 deadlock / robust deadlock risk”分开。

---

## 2. DES 语义备忘

设 plant 为：

```text
G = (Q, Sigma, delta, q0)
Sigma = Sigma_c union Sigma_uc
Sigma = Sigma_o union Sigma_uo
```

其中：

- `Sigma_c`：controllable events
- `Sigma_uc`：uncontrollable events
- `Sigma_o`：observable events
- `Sigma_uo`：unobservable events

### 2.1 运行时可用信息

partial observation 下，supervisor / controller 不知道真实状态 `q`，只能知道：

```text
observed trace s in Sigma_o^*
previous control decisions
plant model G
current belief B = possible plant states consistent with s and decisions
```

因此任何 safety / non-deadlock 保证都应对 `B` 中所有可能状态成立，而不是只对某一个真实状态或某一条 transition 成立。

### 2.2 Unobservable closure

对 belief `B`，unobservable closure 是：

```text
UR(B) = { q' | exists q in B, exists w in Sigma_uo^*, delta(q, w) = q' }
```

若考虑控制 pattern `gamma`，则：

```text
UR_gamma(B) = closure using events in (gamma union Sigma_uc) intersect Sigma_uo
```

注意：如果某个 unobservable controllable event 被 supervisor 禁用了，它不应进入 `UR_gamma`。如果只是无控制 analysis，则所有事件都视为 enabled。

### 2.3 Observable successor

从 closed belief `C = UR_gamma(B)` 观察到 observable event `a` 后：

```text
RawPost(C, a) = { delta(q, a) | q in C and delta(q, a) defined }
Succ(C, a) = UR_gamma'(RawPost(C, a))
```

`gamma'` 的时序取决于你的模型：

- Mealy / 当前观测后立即更新控制：用下一轮控制 `gamma'`；
- Moore / 控制在下一拍生效：可以把 closure 放到下一轮 expand 时再做。

当前代码没有显式 control pattern，可先用 `gamma = all events`。

---

## 3. Deadlock 判定应分层

当前代码中 `compute_deadlock_status(known_nodes, known_edges)` 的语义是：

```text
known state has at least one known outgoing edge -> nondeadlock
known state has no known outgoing edge -> deadlock
```

这适合动画中表达“目前探索到的信息”，但不适合作为 DES semantic deadlock 判定。建议分成以下几层。

### 3.1 Concrete deadlock

对真实状态 `q`：

```text
Dead(q, gamma) iff Enabled_gamma(q) is empty
```

其中：

```text
Enabled_gamma(q) = { e | delta(q, e) defined and e in gamma union Sigma_uc }
```

无控制 analysis 时，`Enabled(q)` 就是 plant 中所有 outgoing events。

### 3.2 Possible deadlock / may-deadlock

对 belief `B`：

```text
MayDead(B, gamma) iff exists q in UR_gamma(B), Dead(q, gamma)
```

如果目标是 **robust non-deadlock synthesis**，`MayDead` 应视为 losing，因为 hidden reality 可能已经在这个 deadlocked state 中，controller 无法区分。

### 3.3 Certain deadlock / sure-deadlock

```text
SureDead(B, gamma) iff UR_gamma(B) is nonempty and forall q in UR_gamma(B), Dead(q, gamma)
```

这适合诊断语义：“observer 现在能确定系统已经 deadlock”。但它太弱，不足以保证 robust non-deadlock。

### 3.4 Robust non-deadlock

```text
SureNonDead(B, gamma) iff UR_gamma(B) is nonempty and forall q in UR_gamma(B), not Dead(q, gamma)
```

如果做 partial-observation synthesis，这才是当前 belief 下安全地继续的基本条件。

### 3.5 Implicit deadlock / losing belief

有些 belief 当前没有 concrete deadlock，但无论怎么选 admissible control pattern，都会导致 deadlock 或进入 losing successor。这种 belief 可称为 implicit deadlock / losing belief：

```text
Losing(B) iff for every admissible gamma:
  MayDead(B, gamma)
  or exists observable successor a such that Succ(B, gamma, a) is Losing
```

相应的 winning 条件是：

```text
Winning(B) iff exists admissible gamma such that:
  not MayDead(B, gamma)
  and forall possible observable event a, Winning(Succ(B, gamma, a))
```

---

## 4. On-the-fly synthesis / analysis 的正确粒度

论文中的 observable progression 不先构造完整 belief-state DFA，而是在当前 belief 上对所有 hidden completions 做合取 / universal aggregation，并只生成需要探索的 successor。迁移到 DES 后，建议如下。

### 4.1 不建议

不要把 partial observation 理解成：

```text
只看当前真实状态 q 的下一条 outgoing transition
```

原因：当前真实状态不可见，且 unobservable events 可能已经把 plant 带到另一个状态。

也不要在每次运行前强制构造：

```text
完整 observer DFA / 完整 unobservable-reach graph / 全部 belief graph
```

这会失去 on-the-fly 的意义。

### 4.2 建议

每次只对当前 belief 做局部展开：

```text
expand(B):
    C = UR(B)
    classify C
    for each observable event a enabled from some q in C:
        R = RawPost(C, a)
        B_next = UR(R)
        yield a, B_next
```

这里 `UR` 是当前局部 closure。它不是全局 observer，但必须算完整局部 closure，不能只走一条 hidden edge。

---

## 5. 当前代码结构观察

当前 zip 中核心文件如下：

```text
des_core/automata.py       # DFA, DESExample
 des_core/observer.py       # build_observer_dfa, _unobservable_closure
 des_core/deadlock.py       # snapshots, deadlock status, plant/belief animation
 des_core/visualization.py  # PNG/GIF rendering
 examples/non_deadlock.py   # 当前 runner 使用的例子
 des_dfa_on_the_fly.py      # runner
```

主要问题不是代码跑不通，而是语义边界需要更清晰：

1. `observer.py::build_observer_dfa()` 目前是完整 BFS observer construction，不是纯 on-the-fly API。
2. `deadlock.py::compute_deadlock_status()` 以 `known_edges` 判定 deadlock，会把尚未展开 outgoing edge 的节点临时显示为 deadlock；这是 visualization status，不是 semantic DES deadlock。
3. `PartialObservationSnapshot.certain_deadlock` 只表达 “所有 possible states 都是 deadlock”，缺少 robust synthesis 需要的 `possible_deadlock`。
4. `BeliefStateSynthesisSnapshot` 里 closed belief 默认被画成 green，这容易被误读成 semantic non-deadlock；它应该由 belief classifier 决定颜色。
5. 现有 `build_partial_observation_example()` 同时保存 `observer` 和 `original_dfa`，适合展示，但 synthesis 逻辑最好不要依赖“先完整构造 observer”。

---

## 6. 建议新增模块与职责

### 6.1 `des_core/partial_observation.py`

职责：提供 partial-observation 的 on-the-fly belief 操作。

建议公开函数：

```python
Belief = frozenset[State]
ControlPattern = frozenset[Event]

@dataclass(frozen=True)
class ClosureResult:
    belief: Belief
    closure_edges: frozenset[tuple[State, State, Event]]

@dataclass(frozen=True)
class BeliefSuccessor:
    event: Event
    raw: Belief
    closed: Belief
    observable_edges: frozenset[tuple[State, State, Event]]
    closure_edges: frozenset[tuple[State, State, Event]]


def enabled_under_control(plant: DFA, state: State, gamma: ControlPattern | None) -> list[tuple[Event, State]]:
    ...


def unobservable_closure(
    plant: DFA,
    seeds: Iterable[State],
    observable: frozenset[Event],
    gamma: ControlPattern | None = None,
) -> ClosureResult:
    ...


def observable_successors(
    plant: DFA,
    belief: Belief,
    observable: frozenset[Event],
    gamma: ControlPattern | None = None,
) -> list[BeliefSuccessor]:
    ...
```

这样 `observer.py` 和 `deadlock.py` 都可以复用同一套 UR/Post 逻辑。

### 6.2 `des_core/deadlock_semantics.py`

职责：语义上的 concrete / belief deadlock 分类。

```python
from enum import Enum, auto

class BeliefDeadlockKind(Enum):
    EMPTY_BELIEF = auto()
    SURE_NONDEADLOCK = auto()
    POSSIBLE_DEADLOCK = auto()
    CERTAIN_DEADLOCK = auto()

@dataclass(frozen=True)
class BeliefDeadlockStatus:
    kind: BeliefDeadlockKind
    closed_belief: frozenset[State]
    deadlocked_states: frozenset[State]
    nondeadlocked_states: frozenset[State]


def is_concrete_deadlock(plant: DFA, state: State, gamma: ControlPattern | None = None) -> bool:
    return not enabled_under_control(plant, state, gamma)


def classify_belief_deadlock(
    plant: DFA,
    belief: Belief,
    observable: frozenset[Event],
    gamma: ControlPattern | None = None,
) -> BeliefDeadlockStatus:
    closure = unobservable_closure(plant, belief, observable, gamma).belief
    dead = frozenset(q for q in closure if is_concrete_deadlock(plant, q, gamma))
    nondead = closure - dead
    if not closure:
        kind = BeliefDeadlockKind.EMPTY_BELIEF
    elif len(dead) == 0:
        kind = BeliefDeadlockKind.SURE_NONDEADLOCK
    elif len(nondead) == 0:
        kind = BeliefDeadlockKind.CERTAIN_DEADLOCK
    else:
        kind = BeliefDeadlockKind.POSSIBLE_DEADLOCK
    return BeliefDeadlockStatus(kind, closure, dead, nondead)
```

### 6.3 `des_core/nondeadlock_synthesis.py`

职责：如果要从 analysis 走向 synthesis，新增 AND-OR / safety game solver。

```python
@dataclass(frozen=True)
class StrategyStep:
    belief: Belief
    gamma: ControlPattern
    successors: dict[Event, Belief]

@dataclass(frozen=True)
class SolveResult:
    winning: bool
    strategy: dict[Belief, StrategyStep]
    losing_beliefs: frozenset[Belief]


def admissible_control_patterns(plant: DFA, belief: Belief) -> Iterable[ControlPattern]:
    # always include uncontrollable implicitly; gamma only needs controllable subset
    ...


def solve_nondeadlock_game_on_the_fly(
    plant: DFA,
    observable: frozenset[Event],
) -> SolveResult:
    ...
```

第一版可以不做复杂 fixpoint，只实现 DFS + memoization；遇到 cycle 时先用 optimistic safety-game handling 或显式三色标记。若只是 finite reachable graph，也可以 on-the-fly 生成边，然后做标准 greatest fixpoint。

---

## 7. 文件级修改建议

### 7.1 `des_core/automata.py`

建议新增受控 enabled API，避免到处手写 event 过滤：

```python
def enabled_under(self, state: State, allowed: frozenset[Event] | None = None) -> Iterable[tuple[Event, State]]:
    for event, target in self.enabled(state):
        if allowed is None or event in allowed or event in self.uncontrollable:
            yield event, target
```

注意：如果 `allowed` 表示完整 enabled set，应明确是否包含 uncontrollable。更安全的命名是：

```python
def enabled_after_control(self, state: State, enabled_controllable: frozenset[Event] | None = None)
```

### 7.2 `des_core/observer.py`

建议把私有 `_unobservable_closure()` 移到 `partial_observation.py`，并返回 closure edges。`build_observer_dfa()` 可以保留，但改成使用新的 `observable_successors()`：

```python
for successor in observable_successors(plant, belief, observable):
    transitions[(source_name, successor.event)] = _belief_name(successor.closed)
```

同时新增：

```python
class OnTheFlyObserverExplorer:
    def initial(self) -> Belief: ...
    def expand(self, belief: Belief) -> list[BeliefSuccessor]: ...
```

这样动画和 synthesis 都不需要先完整构造 observer。

### 7.3 `des_core/deadlock.py`

建议重命名当前函数：

```python
compute_deadlock_status -> compute_known_edge_status
```

并在 docstring 中说明它是 visualization / discovered graph status。

`PartialObservationSnapshot` 建议扩展为：

```python
@dataclass(frozen=True)
class PartialObservationSnapshot:
    ...
    deadlock_kind: BeliefDeadlockKind
    possible_deadlock_states: frozenset[State]
    certain_deadlock: bool
```

`make_partial_observation_snapshots()` 中，不要只算：

```python
certain_deadlock = all(not plant.enabled_targets(state) for state in belief)
```

应改成：

```python
status = classify_belief_deadlock(plant, belief, observable)
```

若保留动画中的 `known_nodes/known_edges`，则把 known-edge status 和 semantic status 同时显示，但不要混用。

### 7.4 `des_core/visualization.py`

建议新增颜色 / legend：

```text
green  = sure non-deadlock belief
orange = possible deadlock belief
red    = certain deadlock belief
purple dashed = unobservable closure edge
blue/black solid = observable edge
```

对于 `BeliefStateSynthesisSnapshot`，不要把所有 closed beliefs 直接画成 green。closed 只是“已 closure-normalized”，不是“safe”。

### 7.5 `examples/non_deadlock.py`

建议增加最小 counterexample，用来测试 partial observation 下的 may-deadlock：

```text
q0 --u(unobservable)--> q_bad
q0 --a(observable)--> q_good
q_bad has no outgoing events
```

初始 belief closure 为 `{q0, q_bad}`。它不是 certain deadlock，但它是 possible deadlock；robust non-deadlock synthesis 应视为 unsafe。

### 7.6 `README.md`

建议新增一段明确区分：

```text
Known-edge deadlock: only for animation of discovered graph.
Semantic deadlock: based on plant enabled events under current control pattern.
Partial-observation robust non-deadlock: all states in current closed belief must be non-deadlock.
```

### 7.7 仓库清理

建议把 `__pycache__/` 和生成的 `outputs/` 从源码包中移除，并加入：

```gitignore
__pycache__/
*.pyc
outputs/
```

---

## 8. On-the-fly non-deadlock solver 大纲

### 8.1 无控制版本：只做 belief-level analysis

```python
def analyze_on_the_fly(plant: DFA, observable: frozenset[Event]) -> list[Snapshot]:
    B0 = unobservable_closure(plant, {plant.initial}, observable).belief
    frontier = deque([B0])
    visited = set()

    while frontier:
        B = frontier.popleft()
        if B in visited:
            continue
        visited.add(B)

        status = classify_belief_deadlock(plant, B, observable)
        capture(B, status)

        if status.kind == BeliefDeadlockKind.CERTAIN_DEADLOCK:
            continue

        for succ in observable_successors(plant, status.closed_belief, observable):
            capture_successor(B, succ)
            if succ.closed not in visited:
                frontier.append(succ.closed)
```

这个版本适合当前 demo：展示 observer / belief 的 on-the-fly 生成，并正确显示 possible / certain deadlock。

### 8.2 有控制版本：做 robust non-deadlock synthesis

```python
def is_winning(B: Belief) -> bool:
    if B in memo:
        return memo[B]
    if B in visiting:
        return True  # safety objective: cycle without bad state can be provisionally okay

    visiting.add(B)

    for gamma in admissible_control_patterns(plant, B):
        status = classify_belief_deadlock(plant, B, observable, gamma)
        if status.kind in {EMPTY_BELIEF, POSSIBLE_DEADLOCK, CERTAIN_DEADLOCK}:
            continue

        successors = observable_successors(plant, status.closed_belief, observable, gamma)
        if all(is_winning(s.closed) for s in successors):
            strategy[B] = StrategyStep(B, gamma, {s.event: s.closed for s in successors})
            memo[B] = True
            visiting.remove(B)
            return True

    memo[B] = False
    visiting.remove(B)
    return False
```

备注：上面是实现大纲。严格 safety game 最好用 greatest fixpoint；DFS 中遇到 cycle 的处理要小心。对于当前小例子，先实现该版本再补单元测试即可。

### 8.3 Control pattern 枚举

```python
def admissible_control_patterns(plant: DFA, belief: Belief) -> Iterable[frozenset[Event]]:
    controllables = sorted(plant.controllable)
    for subset in powerset(controllables):
        yield frozenset(subset)
```

语义上，uncontrollable events 不需要放在 `gamma` 中，因为它们永远不能被禁用。实现时可在 `enabled_under_control()` 里自动加入 `plant.uncontrollable`。

---

## 9. 需要明确的设计选择

### 9.1 “提前 disable” 是否存在？

只有做 supervisory synthesis 时才存在。若只是分析 plant 是否 deadlock，不存在 control decision，所有 events 都按 plant transition relation 处理。

如果做 synthesis，controller 在 belief 上选择 `gamma`，且：

```text
Sigma_uc must always be enabled
controllable events not in gamma are disabled
```

### 9.2 “没有 observable successor” 是否等于 deadlock？

不一定。

如果闭包里还有 unobservable transition 或 unobservable cycle，plant 不是 deadlock，只是 observer 没有看到新 observable event。这更像 livelock / divergence 风险，不是 non-deadlock 意义下的 deadlock。

正确判断应看：

```text
forall q in closed belief, Enabled_gamma(q) 是否为空
```

不是只看 observable successor 是否为空。

### 9.3 “possible deadlock” 是否要判 unsafe？

取决于任务：

- 诊断：只在 `certain_deadlock` 时说“确定 deadlock”。
- robust synthesis：只要 `possible_deadlock` 就应判 unsafe，因为 hidden state 可能已经 deadlock。

当前项目如果目标是“合成保证 non-deadlock 的 supervisor”，建议采用 robust synthesis 语义。

### 9.4 “unobservable reach 是否应该完整计算？”

应该完整计算当前局部 closure：

```text
UR_gamma(B)
```

但不应预先计算全局 observer / 全局 unobservable reach graph。这个区别是 on-the-fly 实现的关键。

---

## 10. 推荐实施顺序

### Milestone 1：抽离 partial-observation 基础函数

新增 `des_core/partial_observation.py`：

- `unobservable_closure()`
- `observable_successors()`
- `enabled_under_control()`
- `BeliefSuccessor`, `ClosureResult`

把 `observer.py` 和 `deadlock.py` 里重复的 closure 逻辑替换掉。

### Milestone 2：加入 semantic deadlock classifier

新增 `des_core/deadlock_semantics.py`：

- `BeliefDeadlockKind`
- `BeliefDeadlockStatus`
- `is_concrete_deadlock()`
- `classify_belief_deadlock()`

更新 snapshot，显示 `sure / possible / certain`。

### Milestone 3：保留完整 observer，但新增 on-the-fly explorer

`build_observer_dfa()` 可以继续作为对照 / debug 工具，但 synthesis 和动画优先使用：

```python
OnTheFlyObserverExplorer.expand(B)
```

### Milestone 4：实现 robust non-deadlock synthesis

新增 `des_core/nondeadlock_synthesis.py`，先做小规模 AND-OR / fixpoint solver。

### Milestone 5：补测试与示例

建议测试：

1. unobservable closure 包含所有 hidden reachable states。
2. unobservable cycle 不会死循环。
3. possible deadlock 与 certain deadlock 能区分。
4. disabled controllable event 不进入 `UR_gamma`。
5. observer full construction 与 on-the-fly expansion 在 reachable beliefs 上一致。
6. 只保留 non-deadlock 语义。

---

## 11. 最小测试例建议

### 11.1 Possible but not certain deadlock

```text
q0 --u(unobservable)--> q_bad
q0 --a(observable)--> q_good
q_bad has no outgoing events
q_good --a--> q_good
```

初始 closure：

```text
UR({q0}) = {q0, q_bad}
```

分类：

```text
possible_deadlock = true
certain_deadlock = false
robust_non_deadlock = false
```

### 11.2 No observable successor but not deadlock

```text
q0 --u(unobservable)--> q1
q1 --u(unobservable)--> q0
```

没有 observable successor，但每个状态都有 outgoing unobservable event，所以不是 non-deadlock 意义下的 deadlock。

### 11.3 Control disables hidden escape

```text
q0 --c_unobs(controllable, unobservable)--> q1
q0 --a_obs(uncontrollable, observable)--> q2
```

如果 `c_unobs` 被禁用，则 `UR_gamma({q0})` 不应包含 `q1`。

---

## 12. 与论文思想的 DES 对应关系

| 论文中的对象 | DES 改写 |
|---|---|
| observable variables `Po` | observable events `Sigma_o` / observed event trace |
| unobservable variables `Pu` | unobservable events `Sigma_uo` / hidden event traces |
| belief-state DFA | observer / belief transition system |
| observable progression `fpObs` | `Succ(B, a) = UR(Post(UR(B), a))` |
| universal quantification over hidden variables | belief 中保留所有 hidden-reachable states，并对所有可能状态检查安全 |
| on-the-fly game solving | 不先构造完整 observer；只在 solver 需要时展开当前 belief |
| MTBDD terminal conjunction | DES 中可对应为 successor belief set union / closure aggregation |

---

## 13. 最终建议

当前代码已经很适合作为可视化 demo。下一步最重要的修改不是重画图，而是把语义层拆清楚：

```text
visualization discovery status
!= semantic DES deadlock status
!= partial-observation robust synthesis losing status
```

建议优先实现：

1. `partial_observation.py`：统一 UR / Post / Succ。
2. `deadlock_semantics.py`：区分 sure-nondeadlock、possible-deadlock、certain-deadlock。
3. 修改 `deadlock.py` snapshots：同时记录 discovered status 和 semantic belief status。
4. 修改 visualization：closed belief 不再默认 green，而是按 semantic status 着色。
5. 后续再做 `nondeadlock_synthesis.py`：对 control pattern 做 OR，对 observable successor 做 AND。

这样可以同时满足：

- 不预先构造完整 observer；
- 不错误地只看真实状态的一条 edge；
- partial observation 下对 hidden possibilities sound；
- 保持项目语义集中在 non-deadlock。
