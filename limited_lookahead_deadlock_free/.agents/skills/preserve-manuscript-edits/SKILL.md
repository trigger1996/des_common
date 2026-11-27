---
name: preserve-manuscript-edits
description: Preserve the user's writing and edits when revising this project's manuscript, supplementary material, and reviewer responses.
---

修改本项目论文、supplementary material 和 response 时，不要擅自删除、改写或回退用户已写或修改的内容（包括 Note that、过渡句、注释和批注）；只修改用户明确要求的范围，除非用户的写作存在明显语法问题，此时也只做必要的最小修正。

仅针对 supplementary material 的单栏排版：能在当前栏宽内清晰放下的展示公式优先排成单行；相邻的短公式也可用 `\qquad` 分隔并排，避免不必要的 `align*` 换行。过长的公式保留分行，不通过缩小字号或压缩间距强行塞入单行。保持数学含义、编号和引用不变，修改后编译检查是否出现公式越界（`Overfull \hbox`）。此偏好不自动应用于正文、response 或双栏排版。

在本项目正文、补充材料和作者回复中，单独提及算子时写为 `$\UR(\cdot)$`、`$\NX(\cdot)$`；有下标、上标或具体参数时保留，如 `$\UR_\gamma(\hat{x})$`、`$\NX_{\sigma_o}(x)$`。不改动作者注释、代码标识符或审稿意见原文。将 Full 基准表述为不采用 limited-lookahead mechanism 的 BTS 构造，保留原有部分观测假设；真正的全观测比较例子仍按全观测描述。描述每个可能当前状态均存在允许事件的条件时，使用 `enabled-event condition/check`。

所有文件名含 `original` 的对照文件均为只读，不作修改。

本项目的审稿回复中，感谢审稿人时使用 `We thank the reviewer for ...` 等第三人称表述；回复 AE 时可以直接称 `you`。修改称呼时保留审稿意见原文及作者批注。

结果类别使用 `deadlock-free` 和 `deadlocking`，不使用 `winning` 和 `losing`。`deadlock-free` 表示存在保证闭环无死锁的监督器；`deadlocking` 表示不存在这样的监督器，不表示原 DFA 的所有执行都会死锁。表格可用 `DF` 和 `DL` 并明确解释含义。窗口不足、超时或内存中断不归入 `deadlocking`。保留程序内部的状态值、数据字段和审稿意见原文。

本项目正文、supplementary material 和作者 response 中，不使用 `plant`（包括 `plant model`、`plant state`、`plant structure` 等表述）。按语境改用 `DFA`、`DFA state` 或 `DFA structure`；例如 `plant model` 改为 `DFA`，`known plant model/structure` 改为 `known DFA structure`。此规则适用于新写及修改的作者文字；不改动审稿意见原文、参考文献题名、代码标识符、作者注释或文件名含 `original` 的对照文件。

本项目正文（含摘要、图表标题和结论）禁止出现 `please refer to the supplemented materials`，也禁止 `refer to the supplementary material`、`details/proofs are deferred to the supplementary material` 等任何引导读者查看补充材料的同义表述。必要论证直接写清楚；作者源码注释和独立补充材料本身保留。交付前同时检查去除注释后的 LaTeX 和编译 PDF，涵盖跨行及措辞变体。

本 logical DES 论文遵循作者术语约定：logical system 使用 `control pattern(s)`，不使用 `policy/policies`；作者将 `policy` 留用于随机系统或带权重、时间的系统语境。本规则应用于正文、补充材料和作者回复，按上下文区分单个控制模式、控制模式集合及序列并调整语法。保留审稿意见原文、已发表文献题名、代码标识符、作者源码注释和文件名含 `original` 的只读对照文件。

描述本论文的数值实验时使用 `simulations`，不使用 `tests`。此约定不要求改写数学检验或算法检查。本次论文中不使用 `root` 指代初始决策状态，按语境写为 `initial decision state` 及其控制模式。

正文行文和图表标题优先避免冒号、分号，用自然的完整句或连词衔接。这只是行文偏好，不是禁止所有标点。为执行此偏好，千万不要改动公式和数学记号内部的冒号、分号，也不要改动算法语法、定理和证明的自动标题格式、URL、作者注释、文献题名或用户明确保护的作者信息。

每次完成正文修改后，核对 response 中引用或复述的正文公式、算法及其行号、定理、定义、问题、推论、图、表等编号，与当前正文保持一致。先编译正文，再用其标签生成 response 的引用和公式 tag，并同步更新独立编译用的内嵌标签快照。尽量去掉 manuscript quotation 中的修订 highlight，保留作者回复说明及审稿意见原文。补充材料独立推导的公式保留自身编号，不混同于所引用的正文编号。
