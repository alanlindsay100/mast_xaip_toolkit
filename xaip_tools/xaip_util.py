import os, re, shutil

from .pddl_resources import original_model_loader as model_loader
from .planning import planner, pddl_io, lpg_parser as plan_parser, simulator
from .user_io import metric_descriptor 

PLANNING_TIME_LIMIT=90
REPORT_PLANS=False
USE_OPTIC=True
LOCAL = False

script_dir = os.path.dirname(os.path.abspath(__file__))

temp_file_addon = "_temp_constrained_"
temp_fs_path = script_dir + "/xaip_fs"

def set_local():
 global LOCAL
 LOCAL=True

def get_plan_length(plan):
  max_t = 0.0
  for a in plan:
    t = a.time + a.duration
    if t > max_t:
      max_t = t
  return max_t

def plan_printer(PI, tab="    "):
  return "\n  ".join(map(lambda a: str(a),PI)) 

def get_M_Tag(depth):
  return "l" + str(depth)

def fs_init():
  try:
    shutil.rmtree(temp_fs_path)
  except OSError as e:
    print("Error: %s - %s." % (e.filename, e.strerror))
  os.mkdir(temp_fs_path)
    

def get_new_model_paths(M_TAG):
  new_domain_path = temp_fs_path+"/" + temp_file_addon +"domain" + M_TAG +".pddl"
  new_problem_path = temp_fs_path+"/" + temp_file_addon +"problem" + M_TAG +".pddl"
  return new_domain_path, new_problem_path

def get_plan_path(M_TAG): return temp_fs_path+"/" + temp_file_addon +"plan" + M_TAG + ".txt"
def read_in_plan(M_TAG):
  try:
    PI = plan_parser.parse_plan(open(get_plan_path(M_TAG)).read())
  except Exception as e:
    PI = None 
  return PI


def get_active_functions(M):
  Fsyms = M[0].get_dynamic_functions()
  fs = list(filter(lambda f: f.name in Fsyms, M[1].initial_state.funcs.keys()))
  #for til in M[1].initial_state.tils:
  #  f = til.eff.prop
  #  if not f in fs:
  #    fs.append(f)
  return fs
def get_active_predicates(M):
  Psyms = M[0].get_dynamic_predicates()
  for til in M[1].initial_state.tils:
    p = til.eff.prop.name
    if not p in Psyms:
      Psyms.append(p)
  return Psyms

def load_existing_model(depth):
  M_TAG = get_M_Tag(depth)
  dfn, pfn = get_new_model_paths(M_TAG)
  M = model_loader.get_planning_model(dfn, pfn)
  for a in M[0].actions:
    a.name = re.sub(r'\d+$', '', a.name)
  optic = planner.planner(dfn, M[0], M[1], M[1].goal, True)
  M += (optic.get_optic_actions(M[1].initial_state, time_limit=PLANNING_TIME_LIMIT, client=not LOCAL),)
  for a in M[2]:
    a.predicate = re.sub(r'\d+$', '', a.predicate)
  PI = read_in_plan(M_TAG)
  return M, PI, optic

def make_new_plan(M, M_TAG, write_out=True):
  optic2 = planner.planner(get_new_model_paths(M_TAG)[0], M[0], M[1], M[1].goal, True)
  PIP = run_planner(optic2, M[1].initial_state, code_ret=True)
  if write_out and not PIP.__class__==int:
    s = "\n".join(map(lambda a: str(a), PIP))
    open(get_plan_path(M_TAG), 'w').write(s)
  return PIP

def run_planner(planner, s, code_ret=False):
  if USE_OPTIC:
    PIP = planner.do_optic(s, time_limit=PLANNING_TIME_LIMIT, code_ret=code_ret, client=not LOCAL)
  else:
    PIP = planner.do_tamer(s)
    if not PIP == None:
      for a in PIP:
        a.predicate = re.sub(r'\d+$', '', a.predicate)
  return PIP
  
def write_out_model(M, M_TAG):
  new_domain_path, new_problem_path = get_new_model_paths(M_TAG)
  if not USE_OPTIC:
    for (i,a) in enumerate(M[0].actions): 
      a.name += str(i)
  pddl_io.write_out_domain(new_domain_path, M[0])
  pddl_io.write_out_problem(new_problem_path, M[1], M[1].initial_state, M[1].goal, M[1].metric)

def op(A,M): return op_n(A.predicate, M)
def op_n(op_sym,M): return list(filter(lambda op: op_sym==op.name, M[0].actions))

def just_action_str(x): return " ".join([x.predicate] + x.arguments)

def write_out_plan(PI, M_TAG):
  if not PI == None and not PI.__class__ == int:
    PI_fn = get_plan_path(M_TAG)
    s = "\n".join(map(lambda a: str(a), PI))
    open(PI_fn, 'w').write(s)

def arg_match(args1, args2):
  if not len(args1) == len(args2): return False
  for a1,a2 in zip(args1, args2):
    if a2 == "_": continue
    if not a1 == a2:
      return False
  return True

def _time_str(t):
  return "{:.3f}".format(t)

def set_planner_time_limit(t):
  global PLANNING_TIME_LIMIT
  PLANNING_TIME_LIMIT = t

def prefix_match(s1, s2):
  return s1[:len(s2)] == s2
def any_prefix_match(s1, l):
  for s2 in l:
    if len(s2) > len(s1): 
      continue
    if prefix_match(s1, s2): 
      return True
  return False

def display_metric(m):
  return metric_descriptor.describe_metric(m)

class plan_comparison(object):
  def __init__(self, PI, M, metrics):
    self.metrics = metrics
    self.PI = PI
    if M:
      if not PI.__class__==int:
        self.initial_metric = self.simulate_plan(PI, M)
        for m in metrics:
          print (m)
        print (">>>", self.initial_metric)
  def record_final_plan(self, PIP, M):
    self.PIP = PIP
    if not PIP.__class__==int:
      self.final_metric = self.simulate_plan(PIP, M)
      print ("<<<", self.final_metric)
  def simulate_plan(self, PI, M):
    s = simulator.get_current_metric_state(M, PI)
    return list(map(lambda m: self.evaluate(s, m), self.metrics))
  def evaluate(self, s, m):
    return m.evaluate(s, None)
  def _plan_printer(self, pi):
    return plan_printer(pi)
    
  def __str__(self):
    if REPORT_PLANS:
      return self.__long_str__()
    return self.__metric_str__()
    
  def __metric_str__(self):
    s = "<strong>Why is " + self.get_query() + " in the plan?</strong>\n"
    if self.PIP.__class__==int:
      if self.PIP==-1:
        s += "  If we " + self.get_dont_do_it() +", then <strong>there is no way of solving the problem!</strong>"
      else:
        s += "  If we " + self.get_dont_do_it() +", then <strong>I can't find a plan (within the time limit of " + str(PLANNING_TIME_LIMIT) + " second(s)). It possibly prevents solving the problem.</strong>"
    
    else:
      s += "If we " + self.get_dont_do_it() + " then:\n"
      for i in range(len(self.metrics)):
        lorig = self.initial_metric[i]
        lnew = self.final_metric[i]
        s += "* In terms of the optimisation criteria " + display_metric(self.metrics[i]) + ": "
        # make explanation
        if abs(lorig - lnew) < 1:
          s += "<strong>The plans are comparable.</strong>\n"
        elif lorig < lnew:
          s += "<strong>The plan becomes " + _time_str(lnew - lorig) + " units worse</strong>.\n"
        else:
          s += "<strong>The plan becomes " + _time_str(lorig - lnew) + " units better</strong>.\n"
    return s
    
  def __long_str__(self):
    lorig = get_plan_length(self.PI)
    s = "<strong>Why is " + self.get_query() + " in the plan</strong>:\n" + self._plan_printer(self.PI) + "?\nWhich finishes after: " + str(lorig) + " seconds.\n"
    if self.PIP.__class__==int:
      if self.PIP==-1:
        s += "If we " + self.get_dont_do_it() +", then <strong>there is no way of solving the problem!</strong>"
      else:
        s += "If we " + self.get_dont_do_it() +", then <strong>I can't find a plan (within the time limit of " + str(PLANNING_TIME_LIMIT) + " second(s)). It possibly prevents solving the problem.</strong>"
    
    else:
      lnew = get_plan_length(self.PIP)
      # make explanation
      if lorig < lnew:
        s += "If we " + self.get_dont_do_it() +", <strong>the plan becomes " + _time_str(lnew - lorig) + " seconds longer</strong>. E.g.,\n  " + self._plan_printer(self.PIP) + "\nWhich finishes after: " + str(lnew) + " seconds."
      elif lorig == lnew:
        s += "If we " + self.get_dont_do_it() +", <strong>I can't find a shorter plan.</strong>"
      else:
        s += "If we " + self.get_dont_do_it() +", <strong>I've found a faster plan.</strong> E.g.,\n  " + self._plan_printer(self.PIP) + "\nWhich finishes after: " + str(lnew) + " seconds."
    return s
