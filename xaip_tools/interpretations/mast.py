import itertools, os, math

from .. import xaip_util
from ..xaip_query_response_generators import constraint_support
from ..pddl_resources import planning_types
from ..geometric_support import line_point_near_2_shape_point as near_lib, near_proportion_shapely as near_prop
from ..abstraction import abstraction_fe as abstraction


LOG=True
USE_AREAS_IN_NEAR_CALCULATION=True
ALL_NON_MOVES_COUNTED_AS_NEAR=False

# mapping to model helpers
class located_type:
  def __init__(self, pred, ltype, mover_p, loc_p):
    self.located_pred = pred
    self.loc_type = ltype
    self.mover_p = mover_p
    self.loc_p = loc_p
  def make_predicate(self, m_v, l_v):
    located_pred = planning_types.Predicate(self.located_pred)
    if self.mover_p == 0:
      located_pred.add_var("?mover")
      located_pred.add_var("?location") 
    else:
      located_pred.add_var("?location") 
      located_pred.add_var("?mover")
    return located_pred
    
class temporal_action:
  def __init__(self, a):
    self.a = a
class moving_action:
  def __init__(self, name, mover_p, in_p, out_p):
    self.name = name
    self.mover_p = mover_p
    self.in_p = in_p
    self.out_p = out_p
class moving_type:
  def __init__(self, t, located_pred, moving_action) :
    self.type = t
    self.located_pred = located_pred
    self.moving_action = moving_action
class resource_task_type:
  def __init__(self, task, resource_param, op_arity):
    self.task = task
    self.resource_param = resource_param
    self.op_arity = op_arity
  def instantiate(self, resource, task_id):
    args = ["_"]*self.op_arity
    args[self.resource_param] = resource
    for i, o in zip(self.task[1], task_id): args[i]=o
    return planning_types.PlanAction(-1, self.task[0], args, 0)

# static location naming
class static_location_name(object):
  def get_name(self): pass
  def get_objects(self): pass
  def get_points(self): pass
class location_point(static_location_name):
  def __init__(self, o, point, m):
    self.o = o
    self.point = point
    self.is_modelled = m
  def get_name(self): return self.o
  def get_objects(self): return [self.o]
  def get_points(self): return [self.point]
  def __str__(self): return self.o
class location_label(static_location_name):
  def __init__(self, label, sub_labels, is_area=False):
    self.label = label
    self.sub_labels = sub_labels
    self.is_area = is_area
  def get_name(self): return self.label
  def get_objects(self): return [o for l in self.sub_labels for o in l.get_objects()]
  def get_points(self): return [p for l in self.sub_labels for p in l.get_points()]
  def __str__(self): return self.label + " " + "; ".join(list(map(lambda l: str(l), self.sub_labels)))

# dynamic location label
class moving_objects_name(object):
  def get_name(self): pass
  def get_objects(self): pass
  def get_types(self): pass
class moving_object(moving_objects_name):
  def __init__(self, o, t):
    self.o = o
    self.type = t
  def get_name(self): return self.o
  def get_objects(self): return [self.o]
  def get_types(self): return [self.type]
class moving_object_group(moving_objects_name): 
  def __init__(self, label, dos) :
    self.label = label
    self.objs = dos
  def get_name(self): return self.label
  def get_objects(self):
    return [o for l in self.objs for o in l.get_objects()]
  def get_types(self): return [t for l in self.objs for t in l.get_types()]
class ScenarioMovers:
  def __init__(self):
    self.navigating_entity_map = {}
  def __getitem__(self, key):
    return self.navigating_entity_map[key]
  def __setitem__(self, key, value):
    self.navigating_entity_map[key] = value
  def __delitem__(self, key):
    del self.navigating_entity_map[key]
  def __contains__(self, key):
    return key in self.navigating_entity_map
  def keys(self):
    return self.navigating_entity_map.keys()
  def get_movers(self):
    return list(filter(lambda v: isinstance(v, moving_object), self.navigating_entity_map.values()))
  def get_collections(self):
    return list(filter(lambda v: isinstance(v, moving_object_group), self.navigating_entity_map.values()))
    
# resources 
class resource_allocation_analyser:
  def __init__(self, PI):
    self.PI = PI
  def get_ra(self, tasks):
    m = {}
    for a in self.PI:
      a = [a.predicate] + a.arguments
      if self.is_relevant_action(a, tasks):
        m[tuple(self.get_task(a, tasks))] = self.get_resource(a, tasks)
    return m
  def is_relevant_action(self, a, tasks):
    return a[0] in tasks
  def get_resource(self, a, tasks):
    return a[tasks[a[0]].resource_param + 1]
  def get_task(self, a, tasks):
    return [a[0]] + list(map(lambda i: a[i + 1] , tasks[a[0]].task[1]))

class RM_Extension(xaip_util.plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(RM_Extension, self).__init__(PI, M, metrics)
    self.obj1, self.ra1, self.obj2, self.ra2 = spec
    self.PIP = -1
  def get_query(self):
    return "not make the allocation of " + str(self.ra1) + " to " + str(self.obj1) + " and " + str(self.ra2) + " to " + str(self.obj2)
  def get_dont_do_it(self):
    return "force this allocation"

class MAST:
  def __init__(self, SP, DI):
    self.M = None
    self.scenario_points = SP
    self.resource_interpretation=DI.resource
    self.M_TAG = None
    self.located_entry = None
    self.temporal_actions = []
    self.moving_types = {}
    self.scenario_movers = None
    self.language_extensions = {}
    self.tasks = None

  def get_allocation(self, PI):
    raa = resource_allocation_analyser(PI)
    return raa.get_ra(self.tasks)

  def get_tasks(self): # XXX here we assume that tasks are one object.
    tasks = []
    for a in self.M[2]:
      if a.predicate in self.tasks:
        task = self.tasks[a.predicate]
        param = a.arguments[task.task[1][0]]
        if not param in tasks:
          tasks.append(param)
    print ("THE TASKS: ", tasks)
    return tasks

  def get_task_contexts(self): # XXX here we assume that tasks are one object.
    tasks = {}
    for a in self.M[2]:
      if a.predicate in self.tasks:
        task = self.tasks[a.predicate]
        param = a.arguments[task.task[1][0]]
        if not param in tasks:
          tasks[param] = task
    return tasks

  def init(self, M):
    self.M = M
    E = self.get_edge_endpoints(self.scenario_movers["vehicles"])
    edges = self.make_edges(E)
    print ("NOT initialising SHAPELY..")
    for o in self.scenario_points.get_points():
      print (o.get_name() + " " , end='', flush=True)
      #near_prop.process_line_segments(o.point[:2], edges, self.scenario_points.near)
    print ("")

  def duration_near(self, o1, o2, M, depth):
    if LOG:
      print ("Considering adding monitor for duration " + str(o1) + " near to " + str(o2))
    self.M_TAG = xaip_util.get_M_Tag(depth) 
    self.M = M
    if o1 in self.scenario_movers and o2 in self.scenario_points:
      mo1 = self.scenario_movers[o1]; mo2 = self.scenario_points[o2]
      if isinstance(mo1,moving_objects_name) and isinstance(mo2, static_location_name):
        if self.is_in_model("dn", (mo1,mo2)):
          return self.language_extensions[("dn",mo1.get_name(),mo2.get_name())], None
        f = self.make_function_accumulating_duration_near(mo1,mo2)
        self.language_extensions[("dn",o1,o2)] = f
        if LOG:
          print ("Language extension function:", f)
        nc = self.make_template_entry(o1, o2, f[0], depth)
        if LOG:
          print ("Templates made:", nc)
          print ("Returning function and dot fn:", f, get_dot_fn(mo2.get_name()))
        return f, get_dot_fn(mo2.get_name())
    else:
      print ("WARNING: trying to do duration near with unknown symbol:", o1, o1 in self.scenario_points, o2, o2 in self.scenario_points)
    return None, None

  def distance_travelled(self, o1, M, depth):
    if LOG:
      print ("Considering adding monitor for distance travelled by " + str(o1))
    self.M_TAG = xaip_util.get_M_Tag(depth) 
    self.M = M
    if o1 in self.scenario_movers:
      mo1 = self.scenario_movers[o1]
      if isinstance(mo1,moving_objects_name):
        if self.is_in_model("dt", (mo1,)):
          return self.language_extensions[("dn",mo1.get_name())], False
        f = self.make_function_accumulating_total_distance(mo1)
        self.language_extensions[("dn",o1)] = f
        if LOG:
          print ("Language extension function:", f)
        nc = self.make_template_entry_dt(o1, f[0], depth)
        if LOG:
          print ("Templates made:", nc)
          print ("Returning function:", f)
        return f, True
    print ("WARNING: trying to do distance travelled with unknown symbol:", o1, o1 in self.scenario_movers)
    return None, None


  
  def get_potential_distance_functions(self, fd):
    fd = fd
    pME = self.get_relevant_movers(fd)
    l = []
    for m in pME:
      f = ["distance_travelled_" + m]
      l.append((("monitor total distance of o1 [Extension]", (m,),f), self.generate_distance_function_descriptions(m)))
    return l

  def get_relevant_locations(self, fd):
    l = []
    LEs = self.scenario_points.located_entity_map.keys()
    for p in LEs:
      if p in fd:
        l.append(p)
    return l
  
  def get_relevant_movers(self, fd):
    l = []
    for m in self.scenario_movers.navigating_entity_map:
      if m in fd:
        l.append(m)
    return l
  
  def get_potential_near_functions(self, fd):
    fd = fd
    pME = self.get_relevant_movers(fd)
    pLE = self.get_relevant_locations(fd)
    print (pME, pLE, fd)
    l = []
    for m in pME:
      for loc in pLE:
        print (m, loc)
        f = ["duration_near_" + str(m) + "_2_" + str(loc)]
        l.append((("monitor duration o1 near o2 [Extension]", (m, loc), f), self.generate_near_function_descriptions(m, loc)))
    return l

  def get_potential_functions(self, fd):
    l = self.get_potential_distance_functions(fd)
    l += self.get_potential_near_functions(fd)
    return l


  def is_in_model(self, pred_type, params):
    params = tuple(map(lambda p: p.get_name(), params))
    if (pred_type,) + params in self.language_extensions:
      f = self.get_f_name(pred_type, params)
      for mf in self.M[0].functions:
        if f == mf.name:
          return True
    return False

  #def get_loc(self, l):
  #  return self.mission.name_position[l][:-1]

  def is_compound_name(self, n):
    s = ""
    if n in self.scenario_points:
      mo = self.scenario_points[n]
      if len (mo.get_objects()) > 1:
        return True
    elif n in self.scenario_movers:
      mo = self.scenario_movers[n]
      if isinstance(mo, moving_object_group):
        return True
    return False

  def loc_str(self, o):
    s = ""
    if o in self.scenario_points:
      mo = self.scenario_points[o]
      if len (mo.get_objects()) > 1:
        s = "the "
    s += o
    return s

  def make_edges(self, se_locs):
    edges = []
    for se_loc in se_locs:
      edges.append(tuple(map(lambda l: self.scenario_points[l].point[:2], se_loc)))
    return edges

  def accumulate_proportions_for_edges(self, edges, edge_seg_map, seg_within_map):
    proportions = []
    for i, (p1,p2) in enumerate(edges) :
      total_dist = self._distance(p1, p2)
      within_dist = 0
      for seg in edge_seg_map[(p1,p2)]:
        if seg_within_map[seg]:
          within_dist += self._distance(seg[0], seg[1])
      if total_dist == 0:
        p = 0
      else:
        p = within_dist/total_dist
      proportions.append(p)
    return proportions

  def get_loc_entity_objects(self, o):
    objs = []
    if isinstance(o, location_label):
      if o.is_area:
        objs.append(o)
      else:
        for so in o.sub_labels:
          objs += self.get_loc_entity_objects(so)
    else:
      objs.append(o)
    return objs
    
  def get_shapes(self, objs):
    shapes = []
    for o in objs:
      shapes.append(o.get_points())
      print ("A SHAPE: ", shapes[-1])
    return shapes

  def label_edges_wrt_near_o_ap(self, se_locs, o2):
    edges = self.make_edges(se_locs)
    objs = self.get_loc_entity_objects(o2)
    shapes = self.get_shapes(objs)
    grown_shapes = near_lib.grow_shapes(shapes, self.scenario_points.near)
    proportions = near_lib.identify_proportion_of_edges_within_shapes(edges, grown_shapes)
    make_dot_graph(o2.get_points(), edges, proportions, self.scenario_points.origin, o2.get_name(), self.scenario_points.scale)
    return dict(zip(se_locs, proportions))

  def label_edges_wrt_near_o(self, se_locs, o2):
    points = o2.get_points()
    edges = self.make_edges(se_locs)
    prop_l = [0]*len(edges)
    for p in points:
      for i, v in enumerate(near_prop.process_line_segments(p[:2], edges, self.scenario_points.near)):
        if v > prop_l[i]:
          prop_l[i] = v
    make_dot_graph(points, edges, prop_l, self.scenario_points.origin, o2.get_name(), self.scenario_points.scale)
    return dict(zip(se_locs, prop_l))

  def _distance(self, p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) * self.scenario_points.scale

  def label_edges_wrt_distance(self, se_locs):
    edges = self.make_edges(se_locs)
    m = {}
    for i, (p1,p2) in enumerate(edges) :
      m[se_locs[i]] = self._distance(p1, p2)
    return m

  def label_nodes_wrt_near_o_ap(self, locs, o2):
    loc_points = list(map(lambda l: self.scenario_points[l].point[:2], locs))
    objs = self.get_loc_entity_objects(o2)
    shapes = self.get_shapes(objs)
    grown_shapes = near_lib.grow_shapes(shapes, self.scenario_points.near)
    prop_l = near_lib.identify_points_within_shapes(loc_points, grown_shapes)
    return prop_l

  def label_nodes_wrt_near_o(self, locs, o2):
    o2_points = o2.get_points()
    loc_points = list(map(lambda l: self.scenario_points[l].point[:2], locs))
    prop_l = [0]*len(locs)
    for p in o2_points:
      for i, v in enumerate(near_prop.process_nodes(p[:2], loc_points, self.scenario_points.near)):
        if v > prop_l[i]:
          prop_l[i] = v
    return prop_l

  def get_relevant_move_locs(self, movers, mt):
    return map(lambda a: (a.arguments[mt.moving_action.in_p], a.arguments[mt.moving_action.out_p]), filter(lambda a: a.predicate == mt.moving_action.name and a.arguments[mt.moving_action.mover_p] in movers, self.M[2]))

  def get_edge_endpoints(self, o):
    movers = o.get_objects()
    edges = set()
    for t in o.get_types():
      mt = self.moving_types[t]
      edges.update(self.get_relevant_move_locs(movers, mt))
    return list(edges)

  def generate_near_function_descriptions(self, o1, o2):
    bags = ["duration that","time that","the duration that"],["the " + str(o1), o1],["near","is near","near to","close to","is near to", "is close to", "are near to", "are near"],["the " + str(o2),o2]
    return [' '.join(combo) for combo in itertools.product(*bags)]

  def generate_distance_function_descriptions(self, o1):
    bags = ["distance travelled","total distance","distance gone"],["by","of"],["the " + str(o1), str(o1)]
    return [' '.join(combo) for combo in itertools.product(*bags)]

  def make_template_entry(self, o1, o2, sym, depth):
    s = "---\naction_template:\n  op:\n    operator_symbols: " + sym +"\n"
    combinations = self.generate_near_function_descriptions(o1, o2)
    s += "    verb_alternatives: " + ", ".join(combinations)+ "\n"
    s += "  description: the duration that " + str(o1) + " is near "+ str(o2)+ "\n"
    fn = open(xaip_util.temp_fs_path+"/_function_templates_"+str(depth)+".yaml", "a").write(s)
    return len(combinations)

  def make_template_entry_dt(self, o1, sym, depth):
    s = "---\naction_template:\n  op:\n    operator_symbols: " + sym +"\n"
    combinations = self.generate_distance_function_descriptions(o1)
    s += "    verb_alternatives: " + ", ".join(combinations)+ "\n"
    s += "  description: the total distance travelled by " + str(o1) + "\n"
    fn = open(xaip_util.temp_fs_path+"/_function_templates_"+str(depth)+".yaml", "a").write(s)
    return len(combinations)

  # make a function for proportion of "near"
  # => F: Locs x Locs -> N
  
  


  def make_node_near_prop_function(self, o1, o2):
    fnn = "proportion_node_near_" + o2.get_name()
    fn = planning_types.ParameterList(fnn)
    tl = [self.located_entry.loc_type]
    pl =["?l1"]
    fn.add_parameter((tl, pl))
    self.M[0].add_function(fn)
  
    E = self.get_edge_endpoints(o1)
    s = set()
    for l in E: s.add(l[0]); s.add(l[1])
    N = list(s)
    if USE_AREAS_IN_NEAR_CALCULATION:
      pl = self.label_nodes_wrt_near_o_ap(N, o2)  
    else:
      pl = self.label_nodes_wrt_near_o(N, o2)
    for i, n in enumerate(N):
      self.M[1].initial_state.funcs[planning_types.Proposition(fnn, [n])] = pl[i]
    return fnn
  
  
  def make_edge_near_prop_function(self, o1, o2):
    fne = "proportion_edge_near_" + o2.get_name()
    fe = planning_types.ParameterList(fne)
    tl = [self.located_entry.loc_type]*2
    pl =["?l1","?l2"]
    fe.add_parameter((tl, pl))
    self.M[0].add_function(fe)
    
    E = self.get_edge_endpoints(o1)
    s = set()
    for l in E: s.add(l[0]); s.add(l[1])
    if USE_AREAS_IN_NEAR_CALCULATION:
      m = self.label_edges_wrt_near_o_ap(E, o2)
    else:
      m = self.label_edges_wrt_near_o(E, o2)
    for e in E:
      proportion = m[e]
      self.M[1].initial_state.funcs[planning_types.Proposition(fne, list(e))] = proportion
    return fne

  def make_distance_travelled_function(self, o1):
    fn = "edge_distance"
    f = planning_types.ParameterList(fn)
    tl = [self.located_entry.loc_type]*2 
    pl =["?l1","?l2"]
    f.add_parameter((tl, pl))
    self.M[0].add_function(f)
    E = self.get_edge_endpoints(o1)
    s = set()
    for l in E: s.add(l[0]); s.add(l[1])
    m = self.label_edges_wrt_distance(E)
    state_funcs = []
    for e in E:
      distance = m[e]
      self.M[1].initial_state.funcs[planning_types.Proposition(fn, list(e))] = distance
    return fn

  def get_duration_term(self, mt):
    op = self.M[0].find_operator(mt.moving_action.name)
    try:
      return op.duration.rhs
    except:
      return planning_types.CalcNodeValue(1)

  def get_f_name(self, pred_type, params):
    if pred_type == "dn":
      return "duration_near_" + str(params[0]) + "_2_" + str(params[1])
    elif pred_type == "dt":
      return "distance_travelled_" + str(params[0])
    
  def make_function_accumulating_duration_near(self, o1, o2):
    edge_prop_fn = self.make_edge_near_prop_function(o1, o2)
    movers = o1.get_objects()
    ts = o1.get_types()
    assert len(set(ts)) == 1, "WARNING: mast/duration_near for i move actions: i > 1: Not implemented yet!"
    mt = self.moving_types[ts[0]]
    rop = list(filter(lambda op: mt.moving_action.name==op.name, self.M[0].actions))
    if len(movers) == 1:
      l = len(rop[0].parameters) * ["_"]
      l[mt.moving_action.mover_p] = movers[0]
      A = planning_types.PlanAction(-1, rop[0].name, l, 0)
      ops_A,ops_nA = constraint_support.split_op_by_action(rop, A, self.M, self.M_TAG)
    elif len(movers) == len(self.scenario_movers.get_movers()):
      ops_A = rop
    ## ********************
    ## this bit needs a little special treatment, because the current mask won't work.
    else:
      assert False, "WARNING: mast/duration_near for i movers: 1 < i < all_movers: Not implemented yet!"
    ## ********************
    accumulator_F = "duration_near_" + str(o1.get_name()) + "_2_" + str(o2.get_name())
    self.M[1].initial_state.funcs[planning_types.Proposition(accumulator_F,[])]=0
    self.M[0].add_function(planning_types.ParameterList(accumulator_F))
    edge_prop_F = planning_types.CalcNodeFunc(planning_types.Proposition(edge_prop_fn, (rop[0].parameters.param_list[mt.moving_action.in_p], rop[0].parameters.param_list[mt.moving_action.out_p])))
    duration_term = self.get_duration_term(mt)
    accum_prop = planning_types.CalcNodeFunc(planning_types.Proposition(accumulator_F, []))
    ae = planning_types.FuncIncrease(accum_prop, planning_types.CalcNodeBinaryRel("*",
     duration_term, edge_prop_F))
    for op in ops_A:
      op.at_end_e.append(ae)
    if ALL_NON_MOVES_COUNTED_AS_NEAR:
      point_prop_fn = self.make_node_near_prop_function(o1, o2)
      self.account_for_all_non_move_position(ops_A, point_prop_fn, accum_prop)
    return [accumulator_F]

  def make_first_clip_action(self, x, f, a):
    clip = planning_types.DurativeAction("start_clip_"+self.M_TAG)
    clip.duration = planning_types.Duration(planning_types.CalcNodeValue(0.002))
    clip.at_start_c.append(planning_types.PropGoal(f))
    clip.over_all_c.append(planning_types.PropGoal(x))
    clip.at_end_c.append(planning_types.PropGoal(a))
    
    clip.at_start_e.append(planning_types.PropAssign(x))
    clip.at_end_e.append(planning_types.NegPropAssign(x))
    
    self.M[0].actions.append(clip)
    self.M[1].initial_state.props.append(planning_types.Proposition(f.name, []))
    self.M[1].initial_state.tils.append(planning_types.TIL(0.004, planning_types.NegPropAssign(planning_types.Proposition(f.name, []))))
    return clip

  def make_typical_clip_action(self, x, y, a):
    clip = planning_types.DurativeAction("clip_"+self.M_TAG)
    clip.duration = planning_types.Duration(planning_types.CalcNodeValue(0.004))
    clip.at_end_c.append(planning_types.PropGoal(y))
    clip.over_all_c.append(planning_types.PropGoal(x))
    clip.at_end_c.append(planning_types.PropGoal(a))
    
    clip.at_start_e.append(planning_types.PropAssign(x))
    clip.at_end_e.append(planning_types.NegPropAssign(x))
    clip.at_end_e.append(planning_types.NegPropAssign(y))
    self.M[0].actions.append(clip)
    return clip

  def make_final_clip_action(self, x, y, ex):
    clip = planning_types.DurativeAction("final_clip_"+self.M_TAG)
    clip.duration = planning_types.Duration(planning_types.CalcNodeValue(0.002))
    clip.at_end_c.append(planning_types.PropGoal(y))
    clip.over_all_c.append(planning_types.PropGoal(x))
    
    clip.at_start_e.append(planning_types.PropAssign(x))
    clip.at_end_e.append(planning_types.NegPropAssign(x))
    clip.at_end_e.append(planning_types.NegPropAssign(y))
    clip.at_end_e.append(planning_types.NegPropAssign(ex))
    self.M[0].actions.append(clip)
    return clip

  """
  Relies on predicates for clip (c), action (a) and time (t)
  """
  def make_clip(self, clip_preds):
    c_on_p, a1_done_p, t_0_p, a2_start_p, t_running_p = clip_preds
    a0 = self.make_first_clip_action(c_on_p, t_0_p, a2_start_p)
    ai = self.make_typical_clip_action(c_on_p, a1_done_p, a2_start_p)
    an = self.make_final_clip_action(c_on_p, a1_done_p, t_running_p)
    return a0, ai, an

  def make_clip_predicates(self):
    x = planning_types.Predicate("clip_x_"+self.M_TAG)
    y = planning_types.Predicate("clip_a1e_"+self.M_TAG)
    f = planning_types.Predicate("clip_t0_"+self.M_TAG)
    ae = planning_types.Predicate("clip_a2s_"+self.M_TAG)
    ex = planning_types.Predicate("execution") # assume domains have this already
    for p in x,y,f,ae:
      self.M[0].predicates.append(planning_types.ParameterList(p.name))
    return x, y, f, ae, ex

  def make_counted_idle_predicates(self):
    last_not_idle = planning_types.Predicate("not_idle_last_"+self.M_TAG)
    not_using_counted_a = planning_types.Predicate("no_current_counted_transition_"+self.M_TAG)
    for p in last_not_idle, not_using_counted_a:
      self.M[0].predicates.append(planning_types.ParameterList(p.name))
    return last_not_idle, not_using_counted_a

  def force_clip_for_start_end(self, a, clip_preds):
    c_on_p, a1_done_p, t_0_p, a2_start_p, t_running_p = clip_preds
    a.at_start_c.append(planning_types.PropGoal(c_on_p))
    a.at_end_c.append(planning_types.PropGoal(c_on_p))
    
    a.at_end_e.append(planning_types.PropAssign(a1_done_p))
    a.at_start_e.append(planning_types.PropAssign(a2_start_p))
    a.at_end_e.append(planning_types.NegPropAssign(a2_start_p))
    

  # (* #t (proportion_node_near_survey1 ?location)))
  def make_idle_action(self, point_prop_fn, accum_prop):
    idle_a = planning_types.DurativeAction("idle_" + self.M_TAG)
    idle_a.parameters = planning_types.ParameterList("parameters")
    mover = list(self.moving_types.values())[0]
    idle_a.parameters.add_parameter(([mover.type, self.located_entry.loc_type],["?mover","?location"]))
    idle_a.duration = planning_types.VariableDuration(planning_types.CalcNodeBinaryRel(">=", planning_types.CalcNodeValue("?duration"), planning_types.CalcNodeValue(0)))
    located_pred = mover.located_pred.make_predicate("?mover", "?location")
    idle_a.at_start_c.append(planning_types.PropGoal(located_pred)) # maybe should be over all.. 
    
    point_prop_F = planning_types.CalcNodeFunc(planning_types.Proposition(point_prop_fn, ["?location"]))
    ae = planning_types.FuncIncrease(accum_prop, planning_types.CalcNodeBinaryRel("*", 
     planning_types.CalcNodeTime(), point_prop_F))
    idle_a.continuous_effects.append(ae)
    self.M[0].actions.append(idle_a)
    return idle_a

  def setup_clip(self, counted_A, idle_A):
    to_be_clipped = counted_A + idle_A
    cpreds = self.make_clip_predicates()
    clip_As = self.make_clip(cpreds)

    last_not_idle, not_using_counted_a = self.make_counted_idle_predicates()
    for a in counted_A:
      a.at_start_e.append(planning_types.NegPropAssign(not_using_counted_a))
      a.at_end_e.append(planning_types.PropAssign(not_using_counted_a))
      a.at_end_e.append(planning_types.PropAssign(last_not_idle))
    for a in idle_A:
      a.over_all_c.append(planning_types.PropGoal(not_using_counted_a))
      a.at_start_c.append(planning_types.PropGoal(last_not_idle))
      a.at_start_e.append(planning_types.NegPropAssign(last_not_idle))
    for a in to_be_clipped:
      self.force_clip_for_start_end(a, cpreds)
    #self.M[1].initial_state.props.append(planning_types.Proposition(x.name, []))


  def account_for_all_non_move_position(self, ops_A, point_prop_fn, accum_prop):
    # XXX this is not going to work for survey/observe actions
  
    idle_a = self.make_idle_action(point_prop_fn, accum_prop)
    self.setup_clip(ops_A, [idle_a])
    
    #* Add the effect related to duration near 
    #* Add a proportion function (0 or 1) for each point

  def make_function_accumulating_total_distance(self, o1):
    distance_fn = self.make_distance_travelled_function(o1)
    movers = o1.get_objects()
    ts = o1.get_types()
    assert len(set(ts)) == 1, "WARNING: mast/duration_near for i move actions: i > 1: Not implemented yet!"
    mt = self.moving_types[ts[0]]
    rop = list(filter(lambda op: mt.moving_action.name==op.name, self.M[0].actions))
    if len(movers) == 1:
      l = len(rop[0].parameters) * ["_"]
      l[mt.moving_action.mover_p] = movers[0]
      A = planning_types.PlanAction(-1, rop[0].name, l, 0)
      ops_A,ops_nA = constraint_support.split_op_by_action(rop, A, self.M, self.M_TAG)
    elif len(movers) == len(self.scenario_movers.get_movers()):
      ops_A = rop
    ## ********************
    ## this bit needs a little special treatment, because the current mask won't work.
    else:
      assert False, "WARNING: mast/duration_near for i movers: 1 < i < all_movers: Not implemented yet!"
    ## ********************
    accumulator_F = "distance_travelled_" + str(o1.get_name())
    self.M[1].initial_state.funcs[planning_types.Proposition(accumulator_F,[])]=0
    self.M[0].add_function(planning_types.ParameterList(accumulator_F))
    distance_F = planning_types.CalcNodeFunc(planning_types.Proposition(distance_fn, (rop[0].parameters.param_list[mt.moving_action.in_p],rop[0].parameters.param_list[mt.moving_action.out_p])))
    accum_prop = planning_types.CalcNodeFunc(planning_types.Proposition(accumulator_F, []))
    ae = planning_types.FuncIncrease(accum_prop, distance_F)
    for op in ops_A:
      op.at_end_e.append(ae)
    return [accumulator_F]

  def get_functions(self):
    return list(map(lambda x: [x.name] + x.args , self.M[1].initial_state.funcs.keys()))

  def minimise_function(self, f):
    F = filter(lambda x: xaip_util.arg_match(x, f), self.get_functions())
    F = list(map(lambda f: planning_types.CalcNodeFunc(planning_types.Proposition(f[0],f[1:])), F))
    s = F[0]
    for b in F[1:]:
      s = planning_types.CalcNodeBinaryFunc("+", b, s)
    self.M[1].metric.f = planning_types.CalcNodeBinaryFunc("+", planning_types.CalcNodeBinaryFunc("*", self.M[1].metric.f, 0.001), s)
    #self.M[1].metric.f = planning_types.CalcNodeFunc(s)

  def get_mask_seqs(self, o, ra):
    tcs = self.get_task_contexts()
    M = []
    for alloc in ra:
      M.append([tcs[alloc].instantiate(o, (alloc,))])
    return M

  def force_allocation(self, obj1, ra1, obj2, ra2, M, PI, metrics, DOMAIN_INTERPRETATION, depth):
    comparison = RM_Extension((obj1, ra1, obj2, ra2), PI, M, metrics)
    print ("Forcing allocation of ", obj1, "to",ra1, "and", obj2, "to",ra2)
    M_TAG = xaip_util.get_M_Tag(depth)
    mask_seqs = self.get_mask_seqs(obj1, ra1)
    mask_seqs += self.get_mask_seqs(obj2, ra2)
    s = set()
    for j, mask_seq in enumerate(mask_seqs):
      L, last_sym = constraint_support.identify_seq_in_ops(mask_seq, M, M_TAG + "_" + str(j))
      for (a, t) in L:
        if constraint_support.OP_MOD_CATEGORY.LAST in t and constraint_support.OP_MOD_CATEGORY.TRANSITION in t:
          constraint_support.add_fact_to_goal(M, last_sym)
          # we could also increment counter here instead.
    xaip_util.write_out_model(M, M_TAG)
    PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
    
    comparison.record_final_plan(PIP, M)
    return comparison

  def get_rm_query_templates(self):
    return ["why not allocate #O0 to #O0*, and #O1 to #O1*?"]

def get_dot_fn(oname):
  return xaip_util.temp_fs_path+"/_proportions_" + oname

def make_dot_graph(points, edges, prop_l, ORIGIN, oname, MULT):
  s =  "digraph G {\n"
  for i, p in enumerate(points):
    x,y = p[:2]
    s += "p_"+str(i) +" [label=\"\",shape=star,pos=\"" + str(MULT * (x - ORIGIN[1])) + "," +str(MULT * (y - ORIGIN[1])) +"!\"]\n"
  ns = dict()
  for i, e in enumerate(edges):
    l = []
    for j,p in enumerate(e):
      p = tuple(p)
      if not p in ns: 
        ns[p] = "n" + str(len(ns))
        x,y=p
        s += ns[p] +" [label=\"\",shape=point,pos=\"" + str(MULT * (x - ORIGIN[1])) + "," +str(MULT * (y - ORIGIN[1])) +"!\"]\n"
      l.append(ns[p])
    v = prop_l[i]
    if v > 0.7 : c = "red"
    elif v > 0.4 : c = "orange"
    elif v > 0.2 : c = "gold"
    elif v > 0.1 : c = "green"
    elif v > 0.0 : c = "blue"
    else: c = "black"
    s += l[0] + " -> " + l[1] + " [color=" + c + "]\n"
      
  s += "}"
  fn = get_dot_fn(oname)
  open(fn +".dot",'w').write(s)
     
def initialise_movers(mast, M, SI):
  spatial_interpretation = SI[0] # XXX one type
  SM = ScenarioMovers()
  lpm = {}
  d = spatial_interpretation["located_type"]
  pred = d["located_pred"]
  lpm[pred] = located_type(pred, d["pddl_type"], d["mover_p"], d["loc_p"])
  mast.located_entry = list(lpm.values())[0] # XXX only one located pred
  mam = {}
  d = spatial_interpretation["moving_action"]
  if d["static"]:
    op = d["pddl_op"]
    mam[op] = moving_action(op, d["mover_p"], d["from_p"], d["to_p"])
  else:
    print ("WARNING: Ignoring dynamic move action..")
  movers = []
  d = spatial_interpretation["moving_type"] # XXX only works for one type, one pred etc.
  t = d["type"]
  mast.moving_types[t] = moving_type(t, d["located_pred"], mam[d["moving_actions"]]) # XXX currently one move action
  movers += filter(lambda o: o[1]==t, M[1].objects.items()) # XXX lazy - fails with type hierarchy
  ml = []
  for mover in movers:
    mo = moving_object(mover[0], mover[1])
    SM[mo.get_name()]=mo
    ml.append(mo)
  name = "vehicles"
  SM[name] = moving_object_group(name, ml)
  mast.scenario_movers = SM

def initialise_temporal_entries(mast, M):
  mast.temporal_actions = list(map(lambda a: temporal_action(a.name), M[0].actions))

def initialise_tasks(mast, RI):
  td = {}
  for tt in RI:
    d = tt["task_type"]
    l = d["task_sequence"][0].split(",") # XXX tasks are currently characterised by a single action
    arity = len(l)-1
    mover_p = l.index("MOVER")-1
    id_tup = list(map(lambda e: e[0],filter(lambda e: e[1].startswith("ID"), enumerate(l[1:]))))
    td[d["label"]] = resource_task_type((l[0], id_tup), mover_p, arity)
  print ("TASKS init: ", td)
  mast.tasks = td


def MAST_builder(M, SP, DI, depth):
  mast = MAST(SP, DI)
  initialise_movers(mast, M, DI.spatial)
  initialise_temporal_entries(mast, M)
  initialise_tasks(mast, DI.resource)
  
  return mast
  
