import importlib.util,sys,random
from dataclasses import fields
from des_core.ll_bts import construct_ll_bts
from des_core.automata import DFA
from des_core.implicit_product import ImplicitProductDFA
from examples.non_deadlock import build_small_cycle_example
spec=importlib.util.spec_from_file_location('before','.tmp_ll_bts/ll_bts_before.py');old=importlib.util.module_from_spec(spec);sys.modules['before']=old;spec.loader.exec_module(old)
rng=random.Random(42)
plants=[]
for i in range(60):
 states=frozenset(str(n) for n in range(4));events=frozenset('abc')
 plants.append((DFA(states,'0',events,frozenset(e for e in sorted(events) if rng.random()<.5),frozenset(e for e in sorted(events) if rng.random()<.5),{(q,e):rng.choice(sorted(states)) for q in sorted(states) for e in sorted(events) if rng.random()<.65}),i%5))
plants.extend((ImplicitProductDFA(build_small_cycle_example().dfa,c),h) for c in (1,2) for h in (0,3,7))
for p,h in plants:
 for store in (False,True):
  a=old.construct_ll_bts(p,p.initial,h,store);b=construct_ll_bts(p,p.initial,h,store)
  assert all(getattr(a,f.name)==getattr(b,f.name) for f in fields(a))
print('132 full-field original/optimized comparisons passed')
