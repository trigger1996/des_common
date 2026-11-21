"""User-authorized benchmark variants; original paper builders stay available."""
from dataclasses import replace

from des_core.automata import DFA

# De-duplicate the original designs, allowing state/event renaming and ignoring
# alphabet symbols which occur on no edge. Other requested duplicate checks failed.
REMOVED = {
    'yin2016_fig_1b': '15ACCopac_fig_2a',
    '17TAC-Range_fig_2c': '16WODESmax_fig_2a',
    '24TACopa_fig_1b': '15ACCopac_fig_2b',
}

CHANGES = {
    'yin2016_fig_3b': [('remove_loops',s) for s in ('5^-1','3^2','5^2')],
    'yin2016_fig_3c': [('remove_loops','5')],
    '15ACCopac_fig_1': [('remove','6','o1','6')],
    '15ACCopac_fig_2a': [('remove','6','o1','6')],
    '16CDC_fig_2a_K': [('relabel','3','o','5','c2'),('relabel','1','o','2','c1')],
    '16WODESmax_fig_1a': [('add','5','c2','1')],
    '16WODESmax_fig_1b': [('add','5','c1','1')],
    '16WODESmax_fig_2a': [('add','5','c2','5'),('add','6','c1','6')],
    '16WODESmax_fig_3a_Gprime': [('add','6','c2','6'),('add',"6'",'c2',"6'")],
    '17TAC-Range_fig_2a_G': [('add','5','b','2')],
    '17TAC-Range_fig_2a_K': [('add','5','b','2')],
    '18TACrange_fig_3a': [('add',"8'",'c1',"9'"),('remove','10','o','8')],
    '22TACopaque_fig_1': [('add','4','o3','0'),('control','o3'),('observe','o3')],
    '24TACopa_fig_1a': [('add','5','o1','2')],
    '24TACopa_fig_4': [('add','7','a','5')],
    # "o_s2" in the review denotes the existing state "0_s2" (digit zero).
    '17Mealy_fig_2a': [('add','2','d1','0_s2'),('add','0_s2','s2','0')],
    '17Mealy_fig_2b': [('add','3','d1','3'),('add','3','d2','3')],
    '17Mealy_fig_3a': [('reverse',"1'",'s1','1_s1'),('reverse','0_s1','d1',"1'")],
    '17Mealy_fig_3b': [('remove','0_s1','d2','1'),('add','0_s1','d2','0')],
    '22TAConline_fig_2': [('add','17','u3','14')],
    '22TAClocal_fig_2': [('remove','x5','u6','x1'),('remove','x2','d','x1')],
    '24AutoOpt_fig_2': [('remove_loops','q4')],
    '20CDC2_fig_2a': [('add','10','a','10')],
    '20CDC2_fig_2b': [('add','2','b','2'),('add','6','c','6')],
    '20IFAC1_fig_1': [('add','6','c1','6')],
    '16SEI_fig_1a': [('add','6','b','3'),('add','4','a','2')],
    '16SEI_fig_1b': [('add','8','o','8')],
    '16SEI_fig_4a': [('add','11','c','10'),('add','10','c','11')],
    '23TACsecure_fig_2b': [('remove','3','b','5'),('add','4','b','5')],
}

DEFERRED = {}


def amend_example(example):
    plant=example.dfa
    edges=dict(plant.transitions);controls=set(plant.controllable);observed=set(plant.observable)
    for operation in CHANGES.get(example.name,[]):
        kind,*args=operation
        if kind=='remove_loops':
            q=args[0];assert q in plant.states
            keys=[key for key,t in edges.items() if key[0]==q and t==q]
            assert keys,(example.name,operation)
            for key in keys:del edges[key]
        elif kind in ('remove','relabel','reverse'):
            q,e,t=args[:3];assert edges.get((q,e))==t,(example.name,operation)
            del edges[q,e]
            if kind=='relabel':args=[q,args[3],t]
            elif kind=='reverse':args=[t,e,q]
            else:continue
            q,e,t=args;assert (q,e) not in edges,(example.name,operation)
            edges[q,e]=t
        elif kind=='add':
            q,e,t=args
            assert q in plant.states and t in plant.states and e in plant.events,(example.name,operation)
            assert (q,e) not in edges,(example.name,operation)
            edges[q,e]=t
        elif kind=='control':controls.add(args[0])
        elif kind=='observe':observed.add(args[0])
        else:raise ValueError(operation)
    variant=DFA(plant.states,plant.initial,plant.events,frozenset(controls),frozenset(observed),edges)
    note=(' User-reviewed benchmark variant: topology/partition amended; original paper design retained in plant_original.json.'
          if example.name in CHANGES else
          ' Benchmark adaptation: deadlock-free objective; no topology/partition change requested in the review.')
    return replace(example,dfa=variant,description=example.description+note)


def apply_review_amendments(examples):
    return tuple(amend_example(e) for e in examples if e.name not in REMOVED)
