import sys

from ..pddl_resources import planning_types


dynamic_fs=None
dynamic_ps=None

class merged_list:
  def __init__(self, dp, sp):
    self.dp = dp
    self.sp = sp

  def __contains__(self, item):
    if item.name in dynamic_ps :
      return item in self.dp
    return item in self.sp

class merged_dict:
  def __init__(self, df, sf):
    self.df = df
    self.sf = sf

  def __getitem__(self, el):
    if el in dynamic_fs :
      return self.df[el]
    return self.sf[el]

  def __contains__(self, item):
    if el.name in dynamic_ps :
      return el in self.df
    return el in self.sf
    
class merged_state:
  def __init__(self, ml, md):
    self.props = ml
    self.funcs = md

class op_binding:
  def __init__(self):
    self.op = None

class action_part:
  def __init__(self, a, ob, M):
    self.a = a
    self.ob = ob
    if M:
      self.a_ops = list(filter(lambda op: op.name == self.a.predicate, M[0].actions))
      self.param_map = dict(zip(self.a_ops[0].parameters.param_list, a.arguments))
      self.M = M

  def apply_effect(self, eff, ms, s):
    if eff.__class__ == planning_types.FuncAssign:
      if eff.__class__ == planning_types.FuncIncrease or eff.__class__ == planning_types.FuncDecrease:
        f = get_function(eff.lhs.func, self.param_map)
        val = get_effect_valuation(eff.rhs, self.param_map, ms)
        if eff.__class__ == planning_types.FuncDecrease:
          val = -val
        s.funcs[f] += val
      else:
        f = get_function(eff.lhs.func, self.param_map)
        s.funcs[f] = get_effect_valuation(eff.rhs, self.param_map, ms)
    else:
      eff.apply(ms, s, self.param_map)

  def apply_effects(self, s, ms):
    global te
    if self.ob.op == None:
      self.ob.op = self.get_applicable_op(ms)
      
    for eff in self._get_effect(self.ob.op):
      self.apply_effect(eff, ms, s)

  def get_applicable_op(self, s):
    for op in self.a_ops:
      OK = True
      for prec in self._get_precondition(op) + op.over_all_c:
        if not prec.supported(s, self.param_map):
          OK = False
          break
      if OK == True:
        return op
    print ("*********** SIMULATOR thinks no action could do this!", str(self.param_map) , str(self.a))
    return self.a_ops[0]

  """
  This version is specifically designed to decide between the alternatives - i.e., it assumes it is a plan, and just gets the correct operator.
  """
  def get_applicable_op(self, s):
    if len (self.a_ops) == 1:
      return self.a_ops[0]
    intersect = list() # precondition classes do not have hash/equal methods
    intersect = self._get_precondition(self.a_ops[0]) + self.a_ops[0].over_all_c
    for op in self.a_ops[1:]:
      opp = self._get_precondition(op) + op.over_all_c
      intersect = [p for p in intersect if p in opp]
    
    for op in self.a_ops:
      OK = True
      for prec in self._get_precondition(op) + op.over_all_c:
        if prec in intersect: continue
        if not prec.supported(s, self.param_map):
          OK = False
          break
      if OK == True:
        return op
    print ("*********** SIMULATOR thinks no action could do this!", str(self.param_map) , str(self.a))
    return self.a_ops[0]

class at_start_action (action_part):
  def __init__(self, a, ob, M): 
    super(at_start_action, self).__init__(a, ob, M)
    
  def get_time(self):
    return self.a.time

  def _get_effect(self, op):
    return op.at_start_e

  def _get_precondition(self, op):
    return op.at_start_c

class at_end_action (action_part):
  def __init__(self, a, ob, M): 
    super(at_end_action, self).__init__(a, ob, M)

  def get_time(self):
    return self.a.time + self.a.duration

  def _get_effect(self, op):
    return op.at_end_e

  def _get_precondition(self, op):
    return op.at_end_c

def get_function(p, param_map):
  return p.instantiate(param_map)
def get_effect_valuation(f, param_map, s):
  return f.evaluate(s, param_map)

def get_active_predicates(M):
  Psyms = M[0].get_dynamic_predicates()
  for til in M[1].initial_state.tils:    
    if isinstance (til.eff, planning_types.PropAssign):
      p = til.eff.prop.name
      if not p in Psyms:
        Psyms.append(p)
  return Psyms

def get_active_functions(M):
  Fsyms = M[0].get_dynamic_functions()
  fs = list(filter(lambda f: f.name in Fsyms, M[1].initial_state.funcs.keys()))
  for til in M[1].initial_state.tils:
    if isinstance (til.eff, planning_types.FuncAssign):
      if not til.eff.lhs.func in fs:
        fs.append(til.eff.lhs.func)
  return fs

def extract_dynamic_state(s, M) :
  global dynamic_fs,dynamic_ps
  dynamic_fs = get_active_functions(M)
  dynamic_ps = get_active_predicates(M)
  ds = planning_types.State()
  for p in s.props:
    if p.name in dynamic_ps :
      ds.props.append(p)
  for f in dynamic_fs:
    ds.funcs[f]=s.funcs[f]
  return ds



def get_states_sequence(M, PI, t=sys.maxsize):
  s = M[1].initial_state
  ds = extract_dynamic_state(s, M)
  ms = merged_state(merged_list(ds.props, s.props), merged_dict(ds.funcs, s.funcs))

  v = 0
  action_parts = list()
  for a in PI:
    ob = op_binding()
    action_parts.append(at_start_action(a, ob, M))
    action_parts.append(at_end_action(a, ob, M))
  action_parts.sort(key=lambda a: a.get_time())
  ds.funcs[planning_types.Proposition("total-time",[])] = 0
  print ("&&&&&&&&& Initial state size:", len(s.props) + len(s.funcs), "&&&&&&& Dynamic state size: ", len(ds.props) + len(ds.funcs))
  S=[ds.clone()]
  for a in action_parts:
    if a.get_time() > t:
      break
    a.apply_effects(ds, ms)
    ds.funcs[planning_types.Proposition("total-time",[])] = a.get_time()
    S.append(ds.clone())
  del ms.props, ms.funcs
  del ms
  return S



def get_current_metric_state(M, PI, t=sys.maxsize):
  return get_states_sequence(M, PI, t)[-1]




