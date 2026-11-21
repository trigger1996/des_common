from pathlib import Path
import re

p = Path('[paper]Limited Lookadhead Deadlock-free/Response/technical_implementation_draft.tex')
s = p.read_text(encoding='utf-8')
pos = s.index('\\item \\notused{\\textbf{与完整BTS')
prefix, tail = s[:pos], s[pos:]
# ulem treats an entire nested colour macro as an unbreakable unit. Strip only
# those inner colour wrappers in the newly annotated spans; preserve their text.
def unwrap_colors(value):
    for command in (r'\comment{', r'\highlight{'):
        while command in value:
            a = value.index(command)
            i, depth = a + len(command), 1
            while depth:
                depth += (value[i] == '{') - (value[i] == '}')
                i += 1
            value = value[:a] + value[a+len(command):i-1] + value[i:]
    return value

cursor = 0
while True:
    a = tail.find(r'\notused{', cursor)
    if a < 0:
        break
    i, depth = a + len(r'\notused{'), 1
    while depth:
        depth += (tail[i] == '{') - (tail[i] == '}')
        i += 1
    content = unwrap_colors(tail[a+len(r'\notused{'):i-1])
    tail = tail[:a] + '\\notused{' + content + '}' + tail[i:]
    cursor = a + len(r'\notused{') + len(content) + 1
p.write_text(prefix + tail, encoding='utf-8')
