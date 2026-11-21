"""Logical information-node counts, distinct from physical plant states."""


def graph_size_metrics(online,offline):
    result={}
    for prefix,data in (('online',online),('offline',offline)):
        assert data['nodes']==data['D']+data['O']
        result.update({prefix+'_D':data['D'],prefix+'_O':data['O'],prefix+'_nodes':data['nodes'],
            prefix+'_retained_D':data['retained_D'],prefix+'_retained_O':data['retained_O'],
            prefix+'_retained_nodes':data['retained_D']+data['retained_O']})
    for prefix in ('','retained_'):
        on=result['online_'+prefix+'nodes'];off=result['offline_'+prefix+'nodes']
        result[prefix+'nodes_saved']=off-on
        result[prefix+'node_saving']=(off-on)/off if off else None
    return result


def aggregate_graph_sizes(rows):
    fields=('D','O','nodes','retained_D','retained_O','retained_nodes')
    sums={side+'_'+field:sum(r[side+'_'+field] for r in rows)
          for side in ('online','offline') for field in fields}
    def data(side):return {field:sums[side+'_'+field] for field in fields}
    result=graph_size_metrics(data('online'),data('offline'))
    result['aggregation']='Savings of sums, not the arithmetic mean of per-model percentages.'
    return result
