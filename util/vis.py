import networkx as nx
import matplotlib.pyplot as plt

def draw_graph(G, title):
    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(8, 6))

    # 节点颜色（accepting 高亮）
    node_colors = []
    for n in G.nodes():
        if G.nodes[n].get('contains_accepting', False):
            node_colors.append('lightgreen')
        elif G.nodes[n].get('accepting', False):
            node_colors.append('lightyellow')
        else:
            node_colors.append('lightblue')

    nx.draw_networkx_nodes(G, pos, node_size=2000, node_color=node_colors)
    nx.draw_networkx_edges(G, pos, arrows=True)

    # 标签
    if isinstance(list(G.nodes())[0], frozenset):
        labels = {n: str(set(n)) for n in G.nodes()}
    else:
        labels = {n: n for n in G.nodes()}

    nx.draw_networkx_labels(G, pos, labels)

    # 边标签（支持多 action）
    edge_labels = {
        (u, v): ",".join(sorted(d['action']))
        for u, v, d in G.edges(data=True)
    }

    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.title(title)
    plt.axis('off')
    #plt.show()