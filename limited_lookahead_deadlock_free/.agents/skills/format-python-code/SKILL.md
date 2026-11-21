---
name: format-python-code
description: Apply the user's Python spacing and blank-line rules when writing or formatting Python code, preserving existing code content and behavior.
---

# Python代码写作与排版

## 用户指定规则

- 普通赋值及含等号的比较、增量赋值运算符左右加空格，例如 `count = 0`、`a == b`、`count += 1`。
- 函数调用关键字参数、函数定义默认参数及lambda默认参数的等号左右不加空格，例如 `dict(source=node_id, event=event)`、`def run(limit=5):`。不要把它们改成 `event = event`。
- 调用跨多行时也遵守该规则，例如：

  ```python
  dict(source=node_id, event=event, target=node_ids[pair],
       observable=event in plant.observable,
       controllable=event in plant.controllable)
  ```

- 同一行的逗号后加一个空格；逗号后已经换行或紧接闭合括号时不添加行尾空格。
- 逻辑代码块之间留空行，包括函数内部的初始化、检查、循环、条件分支组和返回之间。模块级函数/类之间两行，方法或局部函数之间一行。
- 不拆开同一 `if/elif/else` 或 `try/except/finally` 结构；不在语句续行、字符串内部或单行语句中插入破坏语法的空行。

## 仅排版时的约束

只调整空格、缩进和空行。不得修改标识符、运算符、标点、注释原文、字符串/文档字符串、数值、导入顺序、算法或参数值。不要借格式化删除分号、添加括号或重构控制流。字符串中嵌入的代码模板保持原文。

针对项目Python源码和测试应用规则。排除虚拟环境、Git元数据、依赖目录、运行输出、备份、临时文件和论文归档；不要格式化第三方代码或旧结果快照。

## 应用与校验

可用 [scripts/format_python.py](scripts/format_python.py) 按token调整空白并按AST语句块添加空行，不依赖外部格式化器：

```powershell
python .agents/skills/format-python-code/scripts/format_python.py --root . --check
python .agents/skills/format-python-code/scripts/format_python.py --root . --write --backup tmp/code_format_before.zip --report outputs/code_format_report.json
```

写入前逐文件确认：忽略行号的语法树一致，且除布局token之外的token类型与原文完全一致（包括注释和字面量）。先保存原文件快照，再写入；若检查失败，停止并保留原文件。完成后运行与项目匹配的测试，并检查再次格式化不会产生变化。
