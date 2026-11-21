"""Extract one observation-feedback supervisor and its reachable physical product."""
from collections import deque

from des_core.certified_lookahead import (Choice, CertifiedResult, complete_choice,
                                         executable_choices, validate_policy)


def restore_certified_result(pre, bts):
    """Restore the retained policy from an exported LL-BTS, without re-synthesis."""
    def decode_estimate(values):
        return frozenset(tuple(value) if isinstance(value,list) else value for value in values)
    estimates={n['id']:decode_estimate(n['estimate']) for n in bts['D']}
    observation={n['id']:n for n in bts['O']}
    edges={tuple(e) for e in bts['edges']}
    retained={tuple(e) for e in bts['policy_edges']}
    assert retained <= edges
    constructed={}; policy={}; safe=set()
    for node in bts['D']:
        did=node['id'];estimate=estimates[did]
        options=[];kept=[]
        if node['safe_terminal']:
            assert estimate <= pre.safe
            safe.add(estimate)
        for source,target,label in sorted(edges):
            if source!=did:continue
            obs=observation[target]
            pattern=frozenset(obs['pattern_controllable'])
            assert frozenset(obs['pattern_full'])==pattern|pre.plant.uncontrollable
            successors=tuple(sorted((event,estimates[dest]) for src,dest,event in edges if src==target))
            choice=Choice(pattern,decode_estimate(obs['estimate']),successors)
            assert choice==complete_choice(pre.plant,estimate,pattern)
            options.append(choice)
            if (source,target,label) in retained:kept.append(choice)
        constructed[estimate]=tuple(options)
        if node['retained']:
            policy[estimate]=tuple(kept)
    result=CertifiedResult(status=bts['status'],initial=estimates[bts['initial']],
        horizon=bts['u'],window=decode_estimate(bts['window']),policy=policy,
        safe_terminals=frozenset(safe),decision_count=len(estimates),
        observation_count=len(observation),edge_count=len(edges),
        boundary_choices=bts['boundary_choices'],seconds=0.,
        all_controllable=pre.plant.controllable,constructed_choices=constructed)
    assert {frozenset(p) for p in bts['maximal_root_patterns']}==set(result.maximal_patterns)
    validate_policy(pre,result)
    return result


def build_closed_loop(pre, result):
    """Keep controller memory through hidden events; include every enabled outcome.

    One inclusion-maximal certified pattern is selected at each estimate, with
    largest cardinality then lexicographically largest event tuple breaking ties.
    Safe-terminal certificates are expanded with enable-all continuation so the
    exported physical closed loop is complete, rather than a one-node certificate.
    """
    if result.status != 'winning':
        return dict(status=result.status,initial=None,controller_initial=None,
                    controller=[],controller_edges=[],nodes=[],edges=[],
                    reason='No certified deadlock-free supervisor exists for this model.'
                    if result.status == 'losing' else 'Horizon insufficient for certification.')
    validate_policy(pre,result)
    plant=pre.plant
    memory_ids={result.initial:'C0'}
    queue=deque([result.initial]); chosen={}; memories=[]; controller_edges=[]
    while queue:
        estimate=queue.popleft()
        if estimate <= pre.safe:
            choice=complete_choice(plant,estimate,plant.controllable)
        else:
            options=executable_choices(pre,result,estimate)
            assert options, ('uncertified continuation',estimate)
            choice=max(options,key=lambda c:(len(c.pattern),tuple(sorted(c.pattern))))
        assert choice==complete_choice(plant,estimate,choice.pattern)
        assert not choice.closure & pre.deadlocks
        chosen[estimate]=choice
        memories.append(dict(id=memory_ids[estimate],estimate=sorted(estimate),
            closure=sorted(choice.closure),controllable_pattern=sorted(choice.pattern),
            full_pattern=sorted(choice.pattern|plant.uncontrollable),
            safe_continuation=estimate<=pre.safe))
        for event,target in choice.successors:
            if target not in memory_ids:
                memory_ids[target]='C%d'%len(memory_ids);queue.append(target)
            controller_edges.append([memory_ids[estimate],event,memory_ids[target]])

    initial=(plant.initial,result.initial)
    node_ids={initial:'L0'}; queue=deque([initial]); nodes=[]; edges=[]; disabled=[]
    while queue:
        state,estimate=queue.popleft()
        node_id=node_ids[state,estimate]
        choice=chosen[estimate]
        assert state in choice.closure
        nodes.append(dict(id=node_id,state=state,memory=memory_ids[estimate]))
        enabled=choice.pattern|plant.uncontrollable
        count=0
        for event,target in plant.enabled(state):
            if event not in enabled:
                assert event in plant.controllable
                disabled.append([node_id,event,target]);continue
            target_estimate=(dict(choice.successors)[event] if event in plant.observable else estimate)
            pair=(target,target_estimate)
            assert target in chosen[target_estimate].closure
            if pair not in node_ids:
                node_ids[pair]='L%d'%len(node_ids);queue.append(pair)
            edges.append(dict(source=node_id,event=event,target=node_ids[pair],
                              observable=event in plant.observable,
                              controllable=event in plant.controllable))
            count+=1
        assert count, ('closed-loop deadlock',state,estimate)
    return dict(status='winning',initial='L0',controller_initial='C0',controller=memories,
        controller_edges=controller_edges,nodes=nodes,edges=edges,disabled=disabled,
        selection='One certified maximal pattern per estimate: largest cardinality, then '
                  'lexicographically largest sorted event tuple; safe estimates enable all.',
        semantics='Reachable product (physical DFA state, observation-feedback controller memory); '
                  'hidden events preserve controller memory. All enabled outcomes are included.')
