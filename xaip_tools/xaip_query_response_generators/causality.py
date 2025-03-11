import sys, os, pydot

from ..planning import planner,pddl_io
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *

if os.path.exists('C:/Program Files/Graphviz/'):  
  os.environ["PATH"] += os.pathsep + 'C:/Program Files/Graphviz/bin'

script_dir = os.path.dirname(os.path.abspath(__file__))


# Internal prefixes
PRED_PREFIX_INTERNAL = ["progress_marker_", "op_splitter_"]

class CompEqual:
  def __init__(self, f):
    self.f = f
class CompGreater:
  def __init__(self, f):
    self.f = f    
class CompSmaller:
  def __init__(self, f):
    self.f = f   
class EffAssign:
  def __init__(self, f):
    self.f = f
    self.name=str(f) + ":=v"
  def __str__(self): return self.name
class EffIncrease:
  def __init__(self, f):
    self.f = f
    self.name=str(f) + "+=v"
  def __str__(self): return self.name
class EffDecrease:
  def __init__(self, f):
    self.f = f
    self.name=str(f) + "-=v"
  def __str__(self): return self.name

class PointAction:
  def __init__(self, a, D, is_start=True):
    self.a = a
    self.is_start = is_start
    self.time = {True: self.a.time,
                 False: self.a.time+self.a.duration}[is_start]
    self.make_prop_sets(D.find_operator(a.predicate))
  
  def _get_relevant_eff(self, op): return {True: op.at_start_e, False: op.at_end_e}[self.is_start]
  def _get_relevant_prec(self, op): return {True: (op.at_start_c + op.over_all_c), False: op.at_end_c}[self.is_start]
  
  def make_prop_sets(self, op):
    self.preconditions = list(); self.effects = list()
    paramMap = dict(zip(op.parameters.param_list, self.a.arguments))
    for (l, preds) in [(self.preconditions, self._get_relevant_prec(op)), (self.effects, self._get_relevant_eff(op))]:
      for p in preds:
        if isinstance(p, planning_types.PropGoal) or isinstance(p, planning_types.PropAssign):
          l.append(p.prop.instantiate(paramMap))
        elif isinstance(p, planning_types.CalcNodeBinaryRel):
          f = p.lhs.func.instantiate(paramMap)
          l.append({"<":CompSmaller, "=":CompEqual, ">":CompGreater}[p.rel](f))
        elif isinstance(p, planning_types.FuncAssign):
          f = p.lhs.func.instantiate(paramMap)
          t = EffAssign
          if isinstance(p, planning_types.FuncIncrease):
            t = EffIncrease
          elif isinstance(p, planning_types.FuncDecrease):
            t = EffDecrease
          l.append(t(f))
        else:
          print ("WARNING: causality analysis missing unknown structure: ", p.__class__, p)
  
  def apply(self, s, D):
    op = D.find_operator(self.a.predicate)
    eff = planning_types.ConjEffect(self._get_relevant_eff(op))
    cs = s.clone()
    eff.apply(s, cs, dict(zip(op.parameters.param_list, self.a.arguments)))
    return cs
  
  def __str__(self):
    return "<" + str(self.time) + "> " + str(self.a)

def make_pointed_plan(PI, D):
  A_pointed = [ap for a in PI for ap in (PointAction(a, D), PointAction(a, D, False))]
  A_pointed.sort(key=lambda x: x.time)
  return A_pointed

def extract_time_points(A_points):
  return list(map(lambda ap: ap.time, A_points))

def make_states(A_points, M):
  s = planning_types.State()
  S = [s]
  for ap in A_points:
    s = ap.apply(s, M[0])
    S.append(s)
  return S

def _find_goals(eff, open_goals):
  iz = []
  for i,g in open_goals:
    if isinstance(g, planning_types.Proposition):
      if isinstance(eff, planning_types.Proposition):
        if g == eff:
          iz.append((i,g))
    else:
      if isinstance(g, CompEqual):
        if isinstance(eff, EffAssign) or isinstance(eff, EffIncrease) or isinstance(eff, EffDecrease):
          if g.f == eff.f:
            iz.append((i,g))
      elif isinstance(g, CompGreater):
        if isinstance(eff, EffAssign) or isinstance(eff, EffIncrease):
          if g.f == eff.f:
            iz.append((i,g))
      elif isinstance(g, CompSmaller):
        if isinstance(eff, EffAssign) or isinstance(eff, EffDecrease):
          if g.f == eff.f:
            iz.append((i,g))
  return iz

def process_point_effects(open_goals, ap, S, i):
  pre_state=S[i].props
  E=[]
  to_remove = []
  for eff in ap.effects:
    for j,g in _find_goals(eff, open_goals):
      E.append((i, j, eff))
      if isinstance(eff, planning_types.Proposition) or not eff in pre_state:
        to_remove.append((j,g))
  for e in to_remove: 
    open_goals.remove(e)
  return E

def process_point_preconditions(open_goals, ap, S, i):
  for prec in ap.preconditions:
    open_goals.append((i,prec))

def process_action_point(open_goals, ap, S, i):
  E = process_point_effects(open_goals, ap, S, i)
  process_point_preconditions(open_goals, ap, S, i)
  return E

def make_causal_graph(S, A_points, goal):
  open_goals = []
  N = A_points; E = []
  for i, ap in reversed(list(enumerate(A_points))):
    E += process_action_point(open_goals, ap, S, i)
  return N, E  

def _make_pred(p):
  pred = planning_types.Predicate(p.name)
  pred.vars = list(map(lambda o: "?" + o, p.args))
  return pred

def make_init_action(M, PI):
  a = planning_types.DurativeAction("init")
  a.parameters = planning_types.ParameterList("parameters")
  init = M[1].initial_state.props
  init_funcs = M[1].initial_state.funcs
  objs = list(set([o for p in init for o in p.args]))
  a.parameters.param_list = list(map(lambda o: "?" + o, objs))
  a.parameters.type_list = list(map(lambda o: M[1].objects[o], objs))
  a.at_end_e = list(map(lambda p: planning_types.PropAssign(_make_pred(p)), init))
  a.at_end_e += list(map(lambda p: planning_types.FuncAssign(planning_types.CalcNodeFunc(_make_pred(p)), planning_types.CalcNodeValue(M[1].initial_state.funcs[p])), init_funcs))
  M[0].actions.append(a)
  return planning_types.PlanAction(-1.0, a.name, objs, 0.001)

def get_plan_length(plan):
  max_t = 0.0
  for a in plan:
    t = a.time + a.duration
    if t > max_t:
      max_t = t
  return max_t

def make_goal_action(M, PI):
  a = planning_types.DurativeAction("goal")
  a.parameters = planning_types.ParameterList("parameters")
  try:
    G = M[1].goal.conj
  except:
    G = [M[1].goal]
  #G = list(map(lambda p: p.prop, G))
  objs = set() #list(set([o for p in G for o in p.args]))
  c = list()
  for cond in G:
    try:
      p = cond.prop
      print (p, p.__class__)
      objs.update(p.args)
      c.append(planning_types.PropGoal(_make_pred(p)))
    except:
      p = cond.lhs
      print (p, p.__class__)
      objs.update(p.func.args)
      c.append(cond.__init__(cond.rel, planning_types.CalcNodeFunc(planning_types.PropGoal(_make_pred(p.func))), cond.rhs))
  objs = list(objs)
  a.parameters.param_list = list(map(lambda o: "?" + o, objs))
  a.parameters.type_list = list(map(lambda o: M[1].objects[o], objs))
  a.at_start_c = c
  M[0].actions.append(a)
  max_t = get_plan_length(PI)
  return planning_types.PlanAction(max_t+0.001, a.name, objs, 0.001)

def make_init_and_goal_actions(M, PI):
  a0 = make_init_action(M, PI)
  an = make_goal_action(M, PI)
  return [a0] + PI + [an]

def get_causal_graph(M, PI):
  PI = make_init_and_goal_actions(M, PI)
  A_points = make_pointed_plan(PI, M[0])
  #T = extract_time_points(A_points)
  S = make_states(A_points, M)
  G = make_causal_graph(S, A_points, M[1].goal)
  return G

def make_dot(iG, effs_on_labels=True):
  N,E = iG
  s = "digraph D {\n"
  nodes = []; n_d = {}
  for n in N:
    if not n.a in n_d:
      n_d[n.a] = [n]
      nodes.append(n.a)
    else:
      n_d[n.a].append(n)
  """import pydot   
  #import networkx as nx
  #import matplotlib.pyplot as plt
  #from networkx.drawing.nx_pydot import graphviz_layout
  #print ("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&77")
  #print (N, E)
  #G = nx.erdos_renyi_graph(30, 0.05)
  #G = nx.DiGraph()
  G = pydot.Dot("my_graph", graph_type="digraph", bgcolor="white")#, rankdir="LR")
  port_map = {True:":w",False:":e"}  
  for i, obj in enumerate(nodes):
    #G.add_node(i, name=obj.predicate + " " + " ".join(obj.arguments))
    G.add_node(pydot.Node(i, label=obj.predicate + " " + " ".join(obj.arguments)))
  for (i,j,l) in list(filter(lambda e: not e[2].name.lower().startswith("ab_node") or e[2].name.lower().startswith("na_node_"), E)):
    #if isinstance(l, planning_types.Proposition):
    #G.add_edge(nodes.index(N[i].a), nodes.index(N[j].a))
    G.add_edge(pydot.Edge(str(nodes.index(N[i].a)) + port_map[ N[i].is_start], str(nodes.index(N[j].a)) + + port_map[ N[j].is_start]))
  #pos = nx.spring_layout(G)
  #pos = graphviz_layout(G, prog='dot')
  #pos = nx.fruchterman_reingold_layout(G)
  #pos = nx.spectral_layout(G)
  #pos = nx.kamada_kawai_layout(G)
  #pos = nx.shell_layout(G)
  G.set_prog('dot')
  graph_output = G.create_dot().decode('utf-8')
  temp_graph = pydot.graph_from_dot_data(graph_output)[0]
  pos = {}
  for node in temp_graph.get_nodes():
    posi = node.get_pos()
    if posi:
      x, y = map(float, posi.replace('"',"").strip().split(','))
      pos[node.get_name()] = (x, y)
  """
  pos={}
  #nx.draw(G, pos, with_labels=True)
  #plt.show()
  port_map = {True:":w",False:":e"}  
  for i,n in enumerate(nodes):
    if n.predicate in ["init", "goal"]:
      label = n.predicate
      if n.predicate == "init":
        c = "green"
      else:
        c = "red"
    else:
      label = str(n.predicate+ " " + " ".join(n.arguments))
      c = "black"
    pos_str = ""
    if str(i) in pos:
       x,y = pos[str(i)]
       pos_str = ",pos=\"" + str(x*0.03) + "," +str(y*0.03) +"!\""
    s += "n" +str(i) + " [label=\"" + label +"\",color=\"" + c +"\"" +pos_str+"]\n"
  for (i,j,l) in list(filter(lambda e: not e[2].name.lower().startswith("ab_node") or e[2].name.lower().startswith("na_node_"), E)):
    n1 = "n" +str(nodes.index(N[i].a)) + port_map[ N[i].is_start]
    n2 = "n" +str(nodes.index(N[j].a)) + port_map[ N[j].is_start]
    col = "black"
    if not isinstance(l, planning_types.Proposition):
      col = "blue"
    label_str = {True:" [color=\"" + col +"\",label=\"" + str(l)+ "\"]", False: ""}[effs_on_labels]
    s += n1 + " -> " + n2 + label_str +"\n"
  s+= "}"
  return s

def get_node_to_points_map(N):
  n_d = {}
  for n in N:
    if not n.a in n_d:
      n_d[n.a] = [n]
    else:
      n_d[n.a].append(n)
  return n_d

def get_relevant_edges(i, E, ipos=0):
  rel_E = []
  for e in E:
    if e[ipos] == i:
      rel_E.append(e)
  return rel_E

def gather_forward_edges(tup_se, tup_NE, seg_E):
  s, e = tup_se
  N, E = tup_NE
  rE = get_relevant_edges(N.index(s), E, 0)
  rE += get_relevant_edges(N.index(e), E, 0)
  seg_E += list(map(lambda e: (N[e[0]], N[e[1]], e[2]), rE))
  return rE

def gather_forward_actions(rE, N, nodes, seg_A):
  jz = list(map(lambda e: e[1], rE))
  candidate_As = list(filter(lambda a: not a in seg_A,nodes.keys()))
  rA = list(filter(lambda a: N.index(nodes[a][0]) in jz or N.index(nodes[a][1]) in jz, candidate_As))
  seg_A += rA
  return rA

def go_forward(G, a, nodes, seg_A, seg_E):
  N,E = G
  rE = gather_forward_edges(nodes[a], G, seg_E)  
  rAs = gather_forward_actions(rE, N, nodes, seg_A)

  for nA in rAs:
    go_forward(G, nA, nodes, seg_A, seg_E)

def extract_causal_segment(G, a):
  N,E = G
  nodes = get_node_to_points_map(N)
  seg_E=list(); seg_A=[a]
  go_forward(G, a, nodes, seg_A, seg_E)
  seg_N = [n for a in seg_A for n in nodes[a]]
  seg_E = list(map(lambda e: (seg_N.index(e[0]),seg_N.index(e[1]), e[2]), seg_E))
  return seg_N, seg_E

def make_and_ouput_dot(fn, G):
  s = make_dot(G)
  open(fn + ".dot", 'w').write(s)

def dotty(M, PI):
  G = get_causal_graph(M, PI)
  make_and_ouput_dot("_graph_out", G)

def gather_all_relevant_goal_edges(G):
  N,E = G
  goal_nodes = list(filter(lambda n: n.a.predicate == "goal", N))
  goal_indices = list(map(lambda n: N.index(n), goal_nodes))
  rel_edges = []
  for i in goal_indices :
    rel_edges += get_relevant_edges(i, E, 1)
  return rel_edges
  
  

def describe_forward_chain(G):
  N,E = G
  s = "Why is A (" + just_action_str(N[0].a) + ") in the plan?\n"
  all_gE = gather_all_relevant_goal_edges(G)
  gE = list(filter(lambda e: not any_prefix_match(e[2].name.lower(), PRED_PREFIX_INTERNAL), all_gE))
  if len(gE) == 0:
    s += "A is in the plan and is part of a redundant sequence (it has no connection to the problem goals)."
    if len(all_gE) > len(gE):
      s += " Moreover, A has been forced into the plan as part of this constraint building."
    return s
  ps = list(map(lambda x: N.index(x), filter(lambda x: x.a == N[0].a, N)))
  direct_goal_edges = list(filter(lambda e: e[0] in ps, gE))
  if len(direct_goal_edges) > 0:
    for (i,j,l) in direct_goal_edges:
      s += "  >> It leads directly to achieving the goal fact: " + str(l) + "\n"
    s += "Overall, the action is in the causal chain of the following goals:"
  else:
    s += "The action is in the causal chain of the following goals:"
  for (i,j,l) in gE:
    s += "\n  >> " + str(l)
  return s

def why_a(M, PI, a, LOCAL):
  A = list(filter(lambda step: step.predicate == a.predicate and arg_match(step.arguments, a.arguments), PI))[0]
  
  N,E = get_causal_graph(M, PI)
  E = list(filter(lambda e: not any_prefix_match(e[2].name.lower(), PRED_PREFIX_INTERNAL), E))
  cG = extract_causal_segment((N,E), A)
  fn = script_dir + "/_whyA_out"
  make_and_ouput_dot(fn, cG)
  if not LOCAL:
    try:
      nfn = script_dir + "/_whyA_out_preproc"
      graph = pydot.graph_from_dot_file(fn+".dot")[0]
      graph.write_dot(nfn+".dot")
      fn = nfn
    except Exception as e:
      print(e,type(e).__name__)
  return describe_forward_chain(cG), fn

def get_query_templates():
  return ["Which goals does #A support?",]
    

if __name__ == '__main__':
  import lpg_parser as plan_parser
  domain_path, problem_path, pi_fn = sys.argv[1:4]
  M = model_loader.get_planning_model(domain_path, problem_path)
  PI = plan_parser.parse_plan(open(pi_fn).read())
  x = why_a(M, PI, PI[4])
  print(x)
  #x = why_a(M, PI, PI[4], True)
  #print "Dot file at: ", x
  
