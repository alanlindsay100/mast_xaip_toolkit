import networkx as nx
import traceback, math, fnmatch
from ..pddl_resources import planning_types as PT
from ..planning import pddl_io, planner, simulator
from ..xaip_util import get_M_Tag, get_new_model_paths
from . import map_component

EPSILON=0.001

"""
A simple single graph abstraction

Our approach assumes that the indicated actions are appropriate for the abstraction. In certain situations, inappropriate structure will be flagged, but we do not perform structural analysis. We assume that there is the map partition and the other parameters. We assume that the move action is not conditioned on numeric effects that it changes. We assume that the action is not conditioned on propositions that it changes, beyond the locatedness, and a proposition that it deletes on starting, and adds on ending. In this case - the macro is conditioned on the prop at the start. Conditions outwith the partition (or only referencing the mover) are otherwise set as over all condtions. This is because they are typcically conditions of the inner actions, and given the lack of precision, that is the best we can do. Over all conditions transfer. Notice if these are effected by the action then it is not a supported action.

The assumption is that the non-partition parameters will be the same for all actions (e.g., a driver). There is the possibility that there could be different passes for each move, and the pass belongs to the mover, or the driver - so we could examine the other parameters and see if the conditions are static, and can be determined by the mover - for now we make strong assumptions.
"""

def op_n(op_sym, M): return list(filter(lambda op: op_sym==op.name, M[0].actions))
def write_out_model(M, dfn, pfn):
  pddl_io.write_out_domain(dfn, M[0])
  pddl_io.write_out_problem(pfn, M[1], M[1].initial_state, M[1].goal, M[1].metric)
def get_o(a, O, M):
  asa = simulator.at_start_action(a, None, None)
  asa.a_ops = O
  asa.param_map = dict(zip(asa.a_ops[0].parameters.param_list, a.arguments))
  return asa.get_applicable_op(M[1].initial_state)
  
def organise_inst_actions(M):
  actions = M[2]
  O = M[0].actions
  m_a = {}
  m_o = {}
  m_o2a = {}
  for o in O:
    m_o2a[o] = []
    if not o.name in m_a: 
      m_a[o.name] = list()
      m_o[o.name] = list()
    m_o[o.name].append(o)
  for a in actions:
    m_a[a.predicate].append(a)
  
  for sym in m_a:
    A = m_a[sym]
    O = m_o[sym]
    for a in A:
      m_o2a[get_o(a, O, M)].append(a)
  return m_o2a
  
class FunctionTable:
  def __init__(self):
    self.duration = None
    self.f_map = {}
    self.metric = None

  def __str__(self):
    return "Duration: " + str(self.duration) + "; Metric: " + str(self.metric) + "; function map: " + str(self.f_map)

class MoveActionStructure:
  def __init__(self, op, holder):
    self.op = op
    self.pop = op.clone()
    self.SI = holder.SI
    self.M = holder.M
    self.o2a_m = holder.o2a_m
    self.mover_dependent=None
    self.populate_structure()
  def populate_structure(self):
    self.analyse_locatedness()
    self.analyse_parameters()
    self.discover_movers()
    self.analyse_effect()
    self.analyse_condition()

  def discover_movers(self):
    A = self.o2a_m[self.op]
    movers = set()
    mi = self.SI["moving_action"]["mover_p"]
    for a in A:
      movers.add(a.arguments[mi])
    self.movers = list(movers)

  def is_param_in_func_term(self, f, p):
    if isinstance(f, PT.CalcNodeValue):
      return False
    elif isinstance(f, PT.CalcNodeFunc):
      return p in f.func.vars
    elif isinstance(f, PT.CalcNodeBinaryFunc):
      return self.is_param_in_func_term(f.lhs, p) or self.is_param_in_func_term(f.rhs, p)

  def get_params_in_func_term(self, f):
    if isinstance(f, PT.CalcNodeValue):
      return []
    elif isinstance(f, PT.CalcNodeFunc):
      return list(f.func.vars)
    elif isinstance(f, PT.CalcNodeBinaryFunc):
      return self.get_params_in_func_term(f.lhs) + self.get_params_in_func_term(f.rhs)
    else:
      print ("Why???", f, f.__class__)
    

  def determine_if_mover_dependent(self):
    mover_p = self.op.parameters.param_list[self.SI["moving_action"]["mover_p"]]
    if mover_p in self.map_partition: return True
    for e in self.pop.at_start_e + self.pop.at_end_e:
      if isinstance(e, PT.FuncAssign):
        if self.is_param_in_func_term(e.lhs, mover_p) or self.is_param_in_func_term(e.rhs, mover_p):
          return True
    return False

  def analyse_parameters(self):
    self.map_partition = mp = map_component.calculate_map_component(self.pop, self.SI) # we've already removed the locatedness precondition
    self.mover_dependent = self.determine_if_mover_dependent()
    params = [i for i in range(len(self.op.parameters.param_list)) if not self.op.parameters.param_list[i] in mp]
    if len(params) > 0:
      print ("WARNING: assumption is that each param in:", params, "is in a 1-1 relationship, and will not vary during the move...")
    params.append(self.SI["moving_action"]["from_p"])
    params.append(self.SI["moving_action"]["to_p"])
    mi = self.SI["moving_action"]["mover_p"]
    if not mi in params:
      params.append(mi)
    params.sort()
    type_list = list(map(lambda i: self.op.parameters.type_list[i], params))
    param_list = list(map(lambda i: self.op.parameters.param_list[i], params))
    self.params = PT.ParameterList("parameters")
    self.params.add_parameter((type_list, param_list))

  def analyse_condition(self):
    enabler = self.pop.at_start_c + self.pop.at_end_c + self.pop.over_all_c
    self.map_condition = map_component.get_map_constraints(enabler, self.map_partition)
    mp = self.op.parameters.param_list[self.SI["moving_action"]["mover_p"]]
    special_case_can_be_separated=[]
    for c in self.map_condition:
      if len(c.prop.vars) == 1 and c.prop.vars[0]==mp:
        special_case_can_be_separated.append(c)
    for c in special_case_can_be_separated:
      self.map_condition.remove(c)
    self.enable_condition = [e for e in enabler if not e in self.map_condition]
    
    self.analyse_connectivity()

  def get_action_tuples(self):
    return self.o2a_m[self.op]

  def discover_lifted_f_effect(self, a, param_map, f):
    args=[]
    for arg in f.func.vars:
      args.append(param_map[arg])
    try:
      return self.M[1].initial_state.funcs[PT.Proposition(f.func.name, args)]
    except Exception as e:
      traceback.print_exc()

  def discover_op_impact_on_function(self, a, f):
    if f.func.name == "total-time":
      return self.function_table_map[a].duration
    ftm = self.function_table_map[a]
    done_something=False
    v=0
    for e in ftm.f_map:
      if e.func.name == f.func.name:
        done_something=True
        tup = list(map(lambda i: a.arguments[i], map(lambda x: self.op.parameters.param_list.index(x), e.func.vars)))
        if f.func.args == tup:
          v += ftm.f_map[e]
        
    if done_something: 
      return v
    try:
      return self.M[1].initial_state.funcs[f.func]
    except Exception as e: 
      traceback.print_exc()


  def evaluate_function(self, a, param_map, f):
    if isinstance(f.func, PT.Predicate) and len(f.func.vars)>0 and f.func.vars[0][0]=="?":
      v = self.discover_lifted_f_effect(a, param_map, f)
    else:
      v = self.discover_op_impact_on_function(a, f)
    return v


  def evaluate_func_on_edge(self, a, param_map, metric):
    v = 0
    if isinstance(metric, PT.CalcNodeValue):
      v = metric.value
    elif isinstance(metric, PT.CalcNodeFunc):
      v = self.evaluate_function(a, param_map, metric)
    elif isinstance(metric, PT.CalcNodeBinaryFunc):
      lhsV = self.evaluate_func_on_edge(a, param_map, metric.lhs)
      rhsV = self.evaluate_func_on_edge(a, param_map, metric.rhs)
      v = PT.CalcNodeBinaryFunc.evalFs[metric.rel]((lhsV,rhsV))
    else:
      print ("WARNING: maa/evaluate_func_on_edge, not implemented for metric exp: ", metric, type(metric))
    return v
    
  def get_action_duration(self, a, ft):
    ft.duration = self.evaluate_func_on_edge(a, dict(zip(self.op.parameters.param_list, a.arguments)), self.op.duration.rhs)
    
  def record_function_effects(self, a, ft):
    param_map = dict(zip(self.op.parameters.param_list, a.arguments))
    for f in self.partition_numeric_effect:
      v = self.evaluate_func_on_edge(a, param_map, f.rhs)
      if isinstance(f, PT.FuncDecrease):
        v = -v
      elif f.__class__ == PT.FuncAssign:
        print ("WARNING: not dealing with assign in move_action_abstraction - doing something wrong!")
      ft.f_map[f.lhs] = v
  
  def evaluate_metric(self, a, ft):
    ft.metric = self.evaluate_func_on_edge(a, None, self.M[1].metric.f)
  
  def analyse_connectivity_set(self, tup, actions):
    self.function_table_map = ftm = {}
    self.edges = edges = []
    self.edge2action_m = ea_m = {}
        
    for a in actions:
      e = tuple(map(lambda i: a.arguments[i], tup))
      if not e in edges: # XXX just using the first one.. 
        edges.append(e)
        ea_m[e] = a
        ft = ftm[a] = FunctionTable()
        self.get_action_duration(a, ft)
        self.record_function_effects(a, ft)
        self.evaluate_metric(a, ft)
  
  def analyse_connectivity(self):
    actions = self.get_action_tuples()
    moverp, fromp, top = self.SI["moving_action"]["mover_p"], self.SI["moving_action"]["from_p"], self.SI["moving_action"]["to_p"]
    if self.mover_dependent:
      tup = (moverp, fromp, top)
    else:
      tup = (fromp, top)
    self.analyse_connectivity_set(tup , actions)
    
  def analyse_effect(self):
    mover_param = self.op.parameters.param_list[self.SI["moving_action"]["mover_p"]]
    from_param = self.op.parameters.param_list[self.SI["moving_action"]["from_p"]]
    to_param = self.op.parameters.param_list[self.SI["moving_action"]["to_p"]]
    macro_params = (mover_param, from_param, to_param)
    self.not_partition_prop_effect = list()
    self.partition_numeric_effect = list()
    for e in self.pop.at_start_e + self.pop.at_end_e:
      if isinstance(e, PT.FuncAssign):
        if e.__class__ == PT.FuncAssign:
          print ("WARNING: not implemented in abstraction - function assignment:", e)
        prams = set(self.get_params_in_func_term(e.lhs)+self.get_params_in_func_term(e.rhs))
        map_intersect = [p for p in prams if p in self.map_partition]
        # XXX The second term is not an efficient way of doing it - just until the alternative (below) is implemented
        if len(map_intersect) > 0 or len (prams) == 0:
          for p in prams:
            if not p in macro_params:
              print ("WARNING: numeric effect overlapping map partition - the abstraction will be poorly modelled.")
          self.partition_numeric_effect.append(e)
        else:
          print ("WARNING: not implemented in abstraction - numeric functions outside of partition.")
      else:
        OK = True
        if len(e.prop.vars) > 0 :
          map_intersect = [p for p in e.prop.vars if p in self.map_partition]
          if len(map_intersect)==1 and map_intersect[0]==mover_param:
            pass
          elif len(map_intersect) > 0:
            print ("WARNING: effects on the partition in abstraction - are not supported (beyond locatedness) on a static graph..", e)
            OK=False
          for p in e.prop.vars:
            if not p in self.params.param_list:
              print ("WARNING: effect on parameters missing from the macro action in abstraction..", e)
              OK=False
        if OK:
          self.not_partition_prop_effect.append(e)
        else:
          print ("WARNING: unsupported in abstraction - prop effect:", e)
    
    

  def analyse_locatedness(self):
    mover_param = self.op.parameters.param_list[self.SI["moving_action"]["mover_p"]]
    from_param = self.op.parameters.param_list[self.SI["moving_action"]["from_p"]]
    to_param = self.op.parameters.param_list[self.SI["moving_action"]["to_p"]]
    for prec in self.op.at_start_c:
      try:
        pred = prec.prop
        if pred.name == self.SI["located_type"]["located_pred"] :
          prec_m_p = pred.vars[self.SI["located_type"]["mover_p"]]
          prec_l_p = pred.vars[self.SI["located_type"]["loc_p"]]
          if prec_m_p == mover_param and prec_l_p == from_param:
            self.pop.at_start_c.remove(prec)
      except: pass
    for eff in self.op.at_start_e:
      try:
        pred = eff.prop
        if pred.name == self.SI["located_type"]["located_pred"] :
          eff_m_p = pred.vars[self.SI["located_type"]["mover_p"]]
          eff_l_p = pred.vars[self.SI["located_type"]["loc_p"]]
          if eff_m_p == mover_param:
            if eff_l_p == from_param:
              assert isinstance(eff, PT.NegPropAssign)
              self.pop.at_start_e.remove(eff)
            else:
              print ("WARNING: move_action_abstraction/analyse_locatedness - wrong model shape!")
      except: pass
    for eff in self.op.at_end_e:
      try:
        pred = eff.prop
        if pred.name == self.SI["located_type"]["located_pred"] :
          eff_m_p = pred.vars[self.SI["located_type"]["mover_p"]]
          eff_l_p = pred.vars[self.SI["located_type"]["loc_p"]]
          assert eff_m_p == mover_param
          if eff_l_p == to_param:
            assert isinstance(eff, PT.PropAssign)
            self.pop.at_end_e.remove(eff)
          else:
            assert False
      except: pass
    print (self.pop)

class MoveActionAbstraction:

  def __init__(self, M, DOMAIN_INTERPRETATION):
    self.M=M
    self.spatial=DOMAIN_INTERPRETATION.spatial
    self.abstraction = DOMAIN_INTERPRETATION.abstraction
    self.cid = 0
    self.abstract_actions = {}

  def reconstruct_path(self, source, target, predecessor):
    if source == target:
      return [source]
    if predecessor[source].get(target) is None:
      return None  # No path exists
    path = [target]
    while target != source:
      target = predecessor[source][target]
      path.append(target)
    path.reverse()
    return path

  def get_path_attributes(self, graph, path, attr):
    total_v = 0
    for i in range(len(path) - 1):
      u, v = path[i], path[i + 1]
      total_v += graph[u][v][attr]
    return total_v

  def get_path_num_effect(self, path, eff, mas, tup_prefix):
    total_v = 0
    for i in range(len(path) - 1):
      e = path[i], path[i + 1]
      tup = tup_prefix + e
      a = mas.edge2action_m[tup]
      total_v += mas.function_table_map[a].f_map[eff]
    return total_v

  def get_source_target_pairs(self, graph_distance):
    pairs = []
    for source in graph_distance:
      for target in graph_distance[source]:
        if not source == target and not math.isinf(graph_distance[source][target]):
          pairs.append((source, target))
    return pairs

  def add_links_set(self, psym, map_graph, tup_prefix=()):
    _, _, graph_distance = map_graph
    for source, target in self.get_source_target_pairs(graph_distance):      
      self.M[1].initial_state.props.append(PT.Proposition(psym, tup_prefix + (source, target)))
  def add_tuple_link(self, psym, mas):
    if mas.mover_dependent:
      for mover in mas.movers:
        self.add_links_set(psym, self.map_graph[mover], tup_prefix=(mover,))
    else:
      self.add_links_set(psym, self.map_graph)
      
  def add_duration_set(self, psym, map_graph, tup_prefix=()):
    D, graph_predecessor, graph_distance = map_graph
    for source, target in self.get_source_target_pairs(graph_distance):
      path = self.reconstruct_path(source, target, graph_predecessor)
      duration = self.get_path_attributes(D, path, "duration")
      if len(path) > 2:
        duration += + EPSILON*(len(path)-2)
      self.M[1].initial_state.funcs[PT.Proposition(psym, tup_prefix + (source, target))]=duration

  def add_tuple_duration(self, psym, mas):
    if mas.mover_dependent:
      for mover in mas.movers:
        self.add_duration_set(psym, self.map_graph[mover], tup_prefix=(mover,))
    else:
      self.add_duration_set(psym, self.map_graph)
  
  def add_num_eff_set(self, psym, mas, eff, map_graph, tup_prefix=()):
    D, graph_predecessor, graph_distance = map_graph
    for source, target in self.get_source_target_pairs(graph_distance):
      path = self.reconstruct_path(source, target, graph_predecessor)
      v = self.get_path_num_effect(path, eff, mas, tup_prefix)
      self.M[1].initial_state.funcs[PT.Proposition(psym, tup_prefix + (source, target))]=v

  def add_tuple_num_eff(self, psym, mas, eff) :
    if mas.mover_dependent:
      for mover in mas.movers:
        self.add_num_eff_set(psym, mas, eff, self.map_graph[mover], tup_prefix=(mover,))
    else:
      self.add_num_eff_set(psym, mas, eff, self.map_graph)

  def build_map_graph(self, mas):
    if mas.mover_dependent:
      self.map_graph = {}
      for mover in mas.movers:
        D = nx.DiGraph()
        for tup in mas.edges:
          if not tup[0]==mover: continue
          a = mas.edge2action_m[tup]
          ft = mas.function_table_map[a]
          D.add_edge(tup[1], tup[2], duration=ft.duration, metric=ft.metric)
        graph_predecessor, graph_distance = nx.floyd_warshall_predecessor_and_distance(D, weight='metric')
        self.map_graph[mover] = (D, graph_predecessor, graph_distance)
    else:
      D = nx.DiGraph()
      for tup in mas.edges:
        a = mas.edge2action_m[tup]
        ft = mas.function_table_map[a]
        D.add_edge(tup[0], tup[1], duration=ft.duration, metric=ft.metric)
      graph_predecessor, graph_distance = nx.floyd_warshall_predecessor_and_distance(D, weight='metric')
      self.map_graph = (D, graph_predecessor, graph_distance)

  def get_relevant_param_list(self, psym, mas, op):
    dp = PT.ParameterList(psym)
    mover_i = self.SI["moving_action"]["mover_p"]
    from_i = self.SI["moving_action"]["from_p"]
    to_i = self.SI["moving_action"]["to_p"]
    iz = (from_i, to_i)
    if mas.mover_dependent:
      iz = (mover_i,) + iz
    param_list = list(map(lambda i: op.parameters.param_list[i], iz))
    type_list = list(map(lambda i: op.parameters.type_list[i], iz))
    dp.add_parameter((type_list, param_list))
    return dp

  def add_map_condition(self, nop, op, mas):
    self.connected_sym = psym = "connected_" + op.name +"_"+str(self.cid)
    dp = self.get_relevant_param_list(psym, mas, op)
    self.M[0].predicates.append(dp)
    p = PT.Predicate(psym)
    p.vars = dp.param_list
    nop.at_start_c.append(PT.PropGoal(p))
    self.add_tuple_link(psym, mas)
  
  def add_duration(self, nop, op, mas):
    self.duration_sym = psym = "duration_" + op.name +"_"+str(self.cid)
    dp = self.get_relevant_param_list(psym, mas, op)
    self.M[0].functions.append(dp)
    p = PT.Predicate(psym)
    p.vars = dp.param_list
    nop.duration = PT.Duration(PT.CalcNodeFunc(p))
    self.add_tuple_duration(psym, mas)  
  
  def add_numeric_effects(self, nop, op, mas):
    fs = list(map(lambda eff: eff.lhs, mas.partition_numeric_effect))
    for i, f in enumerate(fs):
      self.value_sym = psym = "numeric_effect_" + f.func.name +"_"+str(i)
      dp = self.get_relevant_param_list(psym, mas, op)
      self.M[0].functions.append(dp)
      p = PT.Predicate(psym)
      p.vars = dp.param_list
      nop.at_end_e.append(PT.FuncIncrease(f, p))
      self.add_tuple_num_eff(psym, mas, f)  

  def add_locatedness(self, nop, op, mas):
    mover_param = op.parameters.param_list[self.SI["moving_action"]["mover_p"]]
    from_param = op.parameters.param_list[self.SI["moving_action"]["from_p"]]
    to_param = op.parameters.param_list[self.SI["moving_action"]["to_p"]]
    fp = PT.Predicate(self.SI["located_type"]["located_pred"])
    fp.vars = [mover_param, from_param]
    if self.SI["located_type"]["mover_p"]==1: # XXX assumption of arity two locatedness
      fp.vars.reverse()
    nop.at_start_c.append(PT.PropGoal(fp))
    nop.at_start_e.append(PT.NegPropAssign(fp))
    tp = PT.Predicate(self.SI["located_type"]["located_pred"])
    tp.vars = [mover_param, to_param]
    if self.SI["located_type"]["mover_p"]==1: # XXX assumption of arity two locatedness
      tp.vars.reverse()
    nop.at_end_e.append(PT.PropAssign(tp))

  def split_effect(self, effs, op):
    pre_adds, post_adds, pre_dels, post_dels = list(), list(), list(), list()
    for e in effs:
      pol = not isinstance(e, PT.NegPropAssign)
      if e in op.at_start_e:
        if pol: pre_adds.append(e)
        else: pre_dels.append(e)
      else :
        if pol: post_adds.append(e)
        else: post_dels.append(e)
    return pre_adds, post_adds, pre_dels, post_dels

  def add_not_partition_props(self, nop, op, mas):
    pre_adds, post_adds, pre_dels, post_dels = self.split_effect(mas.not_partition_prop_effect, op)
    for p in pre_adds:
      if p in post_dels:
        pass
      else:
        nop.at_start_e.append(p)
    for p in post_adds:
      nop.at_end_e.append(p)
    nop.at_start_e += pre_dels + post_dels
    for c in list(mas.enable_condition):
      if c in op.at_start_c and isinstance(c, PT.PropGoal) and c.prop in map(lambda d: d.prop, pre_dels + post_dels):
        if c.prop in map(lambda d: d.prop, post_adds):
          nop.at_start_c.append(c)
        else:
          print ("WANRING: This model is not suitable for this abstraction - conditioned on a pred it deletes and doesn't add..", c)
      else:
        nop.over_all_c.append(c)

  def make_new_op(self, op, mas):
    sym = op.name + "_chain"+"_"+str(len(self.abstract_actions))
    nop = PT.DurativeAction(sym)
    nop.parameters = mas.params
    self.add_locatedness(nop, op, mas)
    self.build_map_graph(mas)
    self.add_map_condition(nop, op, mas)
    self.add_numeric_effects(nop, op, mas)
    self.add_not_partition_props(nop, op, mas)
    self.add_duration(nop, op, mas)
    self.M[0].actions.append(nop)
    self.abstract_actions[sym]=(mas, self.map_graph, self.SI)

  def populate_initial_state(self): pass

  def remove_action_from_model(self, op):
    self.M[0].actions.remove(op)

  def abstract_move_action(self, op):
    self.cid += 1
    mas = MoveActionStructure(op, self)
    nop = self.make_new_op(op, mas)
    self.populate_initial_state()
    self.remove_action_from_model(op)
  
  def get_ground_action(self, mas, tup):
    return mas.edge2action_m[tup]
  
  def de_abstract_action(self, a):
    A = []
    mas, map_graph, SI = self.abstract_actions[a.predicate]
    t = a.time
    mover_i = SI["moving_action"]["mover_p"]
    if mas.mover_dependent:
      mover = a.arguments[0]
      D, graph_predecessor, graph_distance = map_graph[mover]
      tup_prefix = (mover, )
    else:
      _, graph_predecessor, _ = map_graph
      tup_prefix = ()
    
    path = self.reconstruct_path(a.arguments[1], a.arguments[2], graph_predecessor)
    for tup in zip(path[:-1],path[1:]):
      ga = self.get_ground_action(mas, tup_prefix + tup)
      d = mas.function_table_map[ga].duration
      if not mas.mover_dependent:
        ga = ga.clone()
        ga.arguments[mover_i] = a.arguments[0]
      ga.time = t
      ga.duration = d
      t += d + EPSILON
      A.append(ga)
    return A
  
  def de_abstract_plan(self, abPI):
    PI = list()
    for a in abPI:
      print (a)
      if a.predicate in self.abstract_actions:
        PI += self.de_abstract_action(a)
      else:
        PI.append(a)
    PI.sort(key=lambda a: a.time)
    return PI
  
  def get_ops_to_abstract(self):
    prefix = "progress_marker_"
    ops=[]
    nops=[]
    for SI in self.spatial:
      for op in op_n(SI["moving_action"]["pddl_op"], self.M):
        OK=True
        for c in op.at_end_e :
          try:
            if c.prop.name.startswith(prefix):
              OK=False
              break
          except:
            pass
            #traceback.print_exc()
        if OK:
          ops.append((op, SI))
        else:
          nops.append((op, SI))
      self.ops2babstracted=ops
      self.ops2ignore=nops
  
  def identify_event_nodes(self): pass
  
  def make_abstract_model(self, depth):
    self.o2a_m = organise_inst_actions(self.M)
    self.get_ops_to_abstract()
    self.identify_event_nodes()
    for op, SI in self.ops2babstracted: 
      self.SI = SI
      self.abstract_move_action(op)
    dfn, pfn = get_new_model_paths(get_M_Tag(depth)+"_EXT")
    write_out_model(self.M, dfn, pfn)
    return dfn, pfn

class RestrictedMoveActionAbstraction (MoveActionAbstraction):
  def __init__(self, M, DOMAIN_INTERPRETATION):
    super().__init__(M, DOMAIN_INTERPRETATION)  
  def get_source_target_pairs(self, graph_distance):
    tups = []
    all_tups = super().get_source_target_pairs(graph_distance)
    i = len(all_tups)
    for (x,y) in all_tups:
      if x in self.decision_nodes and y in self.decision_nodes:
        tups.append((x,y))
    print ("<<<<<< Abstracting from:",i, "tuples, to", len(tups))
    return tups
    

  def process_initial_state_loc_rule(self, r, s, locs):
    pred, i = r.split(" ")
    i = int(i)
    for p in s.props:
      if fnmatch.fnmatch(p.name, pred):
        try:
          locs.add(p.args[i])
        except: pass
  def process_goal_loc_rule(self, r, g, locs):
    pred, i = r.split(" ")
    i = int(i)
    try:
      conj = g.conj
    except:
      conj = [g]
    for p in conj:
      try:
        if p.prop.name == pred:
          locs.add(p.prop.args[i])
      except: pass
      #traceback.print_exc()

  """
  We apply rules to identify important locations. We add rules to deal with constraints, and finally we get related move actions that are not abstractable, and add in their locations. This is essentially treating move actions that are important for propositional constraints, as separate maps. And then including all interfaces between the two maps. As the constraints are usually only defined for small numbers of edges then this will typically not impact greatly on the abstraction.
 
  """

  def identify_event_nodes(self):
    loc_set = set()
    for r in self.abstraction["decision_locations"]:
      if r["scope"] == "initial_state":
        self.process_initial_state_loc_rule(r["rule"], self.M[1].initial_state, loc_set)
      elif r["scope"] == "goal":
        self.process_goal_loc_rule(r["rule"], self.M[1].goal, loc_set)
    irs = [] # This adds locations made important by constraints
    loc_ts = list(map(lambda SI: SI["located_type"]["pddl_type"], self.spatial))
    for p in self.M[0].predicates:
      if p.name.startswith("op_splitter_a_"):
        for i in range(len(p)):
          if p.type_list[i] in loc_ts : # XXX poor type play
            irs.append(p.name + " " + str(i))
    for r in irs:
      self.process_initial_state_loc_rule(r, self.M[1].initial_state, loc_set)
    
    for op, SI in self.ops2ignore:
      from_param = SI["moving_action"]["from_p"]
      to_param = SI["moving_action"]["to_p"]
      for a in self.o2a_m[op]:
        loc_set.add(a.arguments[from_param])
        loc_set.add(a.arguments[to_param])
    self.decision_nodes = list(loc_set)
    print ("******** Identified decision locations:", self.decision_nodes)
    

if __name__ == '__main__':
  d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn = sys.argv[1:]
  print (d_fn, p_fn, d_interp_fn, p_interp_fn)
  xaip_tools.interactive_from_files(d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn)
  """
  Let's get in dfn, pfn, yaml - there might be a disparity between direct yaml and HUME yaml...
  Let's get a move action, and start to work out the idea - look at my notes on the construction of the abstract action.
  
  """
