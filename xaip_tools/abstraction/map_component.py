import networkx as nx
from itertools import combinations
from ..pddl_resources import planning_types as PT

def add_edges(l, G, nodes):
  G.add_edges_from(combinations(l, 2))

def calculate_map_component(op, SI):
    nodes = op.parameters.param_list
    pargs = list(map(lambda c: c.prop.vars, filter(lambda c: isinstance(c, PT.PropGoal), op.at_start_c + op.at_end_c + op.over_all_c)))
    G = nx.Graph()
    G.add_nodes_from(range(len(nodes)))
    from_idx = SI["moving_action"]["from_p"]
    G.add_edge(from_idx,  SI["moving_action"]["to_p"])
    for args in pargs:
      add_edges(list(map(lambda a: nodes.index(a), args)), G, nodes)
    for component in nx.connected_components(G):
      if from_idx in component:
        return list(map(lambda e: nodes[e], component))
      
# XXX ignoring functions  
def get_map_constraints(enabler, partition):
  constraint = []
  for ce in enabler:
    try:
      c = ce.prop
      if len(c.vars)>0 and c.vars[0] in partition:
        constraint.append(ce)
    except: pass
  return constraint

