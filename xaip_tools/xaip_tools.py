import shutil, os, sys, random, traceback, yaml
from threading import Thread


"""
Options for running from HUME/ with either: python3 main.py
 
HUME from defaults
* Running from HUME/main.py option 1
* python3 main.py

XAIP toolkit
* Running from HUME/main.py option 2
* python3 main.py /home/al/HUME/mast_xaip_toolkit/xaip_tools/domains/dl/domain.pddl /home/al/HUME/mast_xaip_toolkit/xaip_tools/domains/dl/pfile14 /home/al/HUME/mast_xaip_toolkit/xaip_tools/domains/dl/Domain_Interpretation.yaml /home/al/HUME/mast_xaip_toolkit/xaip_tools/domains/dl/Scenario_Interpretation_14.yaml /home/al/HUME/mast_xaip_toolkit/xaip_tools/system_settings.yaml

* Running from HUME/main.py option 2
* python3 main.py xaip_tools/domains/uav_scenario/hume_auv.pddl xaip_tools/domains/uav_scenario/p1.pddl xaip_tools/domains/uav_scenario/Domain_Interpretation.yaml xaip_tools/domains/uav_scenario/Scenario_Interpretation.yaml xaip_tools/system_settings.yaml

* Running from HUME/main.py option 2
* python3 main.py xaip_tools/domains/rovers/domain.pddl xaip_tools/domains/rovers/pfile10 xaip_tools/domains/rovers/Domain_Interpretation.yaml xaip_tools/domains/rovers/Scenario_Interpretation_10.yaml xaip_tools/system_settings.yaml

Run the planner with the abstraction
* Running from HUME/main.py option 3
* python3 main.py xaip_tools/domains/rovers/domain.pddl xaip_tools/domains/rovers/pfile1 xaip_tools/domains/rovers/Domain_Interpretation.yaml xaip_tools/system_settings.yaml

"""

from .pddl_resources import planning_types, original_model_loader as model_loader
from .planning import planner, pddl_io, planning_helper, optic_runner as OR, lpg_parser as plan_parser, simulator
from .util.command_runner import execute
from .user_io import template_plan_verbaliser as verbaliser, plan_visualiser, nl2action, template_loader, function_finder
from .abstraction import abstraction_fe as abstraction
from .xaip_query_response_generators import why_A_empirical, A_then_B_empirical, causality, why_not_A_empirical, why_high_function_value_metric, why_high_function_value, why_high_function_value_til, model_extender, why_not_A_before_t_empirical
from .interpretations import mast, scenario_points_loader, interpretation_loader
from .xaip_util import get_new_model_paths, get_M_Tag, get_plan_path, PLANNING_TIME_LIMIT, write_out_plan, plan_printer, run_planner, arg_match, just_action_str, write_out_model,make_new_plan, set_planner_time_limit, load_existing_model, get_active_functions, fs_init, temp_fs_path 

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(script_dir)

LOCAL=False
USE_HTML=True
TEST_HTML=False
USE_NL=True
USE_HYPERLINKS=False
OPEN_COMPARISON=True
MAST=None
METRICS={0:[planning_types.CalcNodeFunc(planning_types.Proposition("total-time",[]))]}
REDUCE_FUNC_10PC=True
OPEN_FIGS=True


# variables storing state between calls
initialised = False
RUN_TUPLE=None
DEPTH=-1
QUERY_LIST=[]
COMPARISON_FNS=list()
LAST_GENERATED_COMPARISON_DOT_FN=None
LAST_GENERATED_PLAN_DOT_FN=None
LAST_GENERATED_LANGUAGE_DOT_FN=None
MODEL_DOT_FN=None
CAUSAL_GRAPH_DOT_FN=None
USE_NUMERIC_CONSTRAINT=True
POSSIBLE_QUERIES_USING_LANGUAGE=list()
DOMAIN_INTERPRETATION=None
SCENARIO_POINTS=None
OPERATOR_TEMPLATES=None
FUNCTION_TEMPLATES=None

def get_model_dot_str():
  if MODEL_DOT_FN==None:
    return None
  return open(MODEL_DOT_FN).read()
def get_causal_graph_dot_str():
  if CAUSAL_GRAPH_DOT_FN==None:
    return None
  return open(CAUSAL_GRAPH_DOT_FN).read()
def get_plan_dot_str():
  if LAST_GENERATED_PLAN_DOT_FN==None:
    return None
  return open(LAST_GENERATED_PLAN_DOT_FN).read()
def get_comparison_dot_str():
  if LAST_GENERATED_COMPARISON_DOT_FN==None:
    return None
  return open(LAST_GENERATED_COMPARISON_DOT_FN).read()
def get_language_extension_dot_str():
  if LAST_GENERATED_LANGUAGE_DOT_FN==None:
    return None
  return open(LAST_GENERATED_LANGUAGE_DOT_FN).read()
def get_example_queries_using_extension():
  return POSSIBLE_QUERIES_USING_LANGUAGE[:]

def _a(a):
  return "(" + " ".join(a) + ")"
def get_all_actions(M):
  return list(map(lambda a: [a.predicate] + a.arguments, M[2]))
def get_plan_actions(pi):
  return list(map(lambda a: [a.predicate] + a.arguments, pi))
def get_not_plan_actions(M, pi):
  return list(filter(lambda a: not a in get_plan_actions(pi), get_all_actions(M)))
def get_functions(M):
  return list(map(lambda x: [x.name] + x.args , M[1].initial_state.funcs.keys())) + list(map(lambda x: x.eff.prop, M[1].initial_state.tils)) # no consideration of assignments in operator effects

def open_pdf(fn):
  execute(["okular", fn])
def open_pdf_t(fn):
  Thread(target = open_pdf, args = (fn, )).start()

def say_list(l):
  if len(l) > 1:
    s = ", ".join(list(map(lambda e: str(e), l[:-1])))
    s += " and " + str(l[-1])
  elif len(l) > 0:
    s = str(l[0])
  else:
    s = ""
  return s

def read_list(s):
  l = []
  if " and " in s:
    s, e = s.split(" and ")
    l.append(e)
  l = s.split(", ") + l
  return l

class constraint_component(object):
  spec_template=list()
  def __init__(self): 
    super(constraint_component, self).__init__()
  def propose_components(self, M, pi):
    pass
  def add_component(self, spec, M, PI, optic, depth):
    pass
  def test_component(self, pi, spec):
    pass
  def report(self):
    if USE_NL and not self._report.__class__ == str:
      self._report._plan_printer = _verbalise_plan
      self.make_plan_dot()
    return str(self._report) + self.get_comparison_hyper()
  def get_match_index(self, pi, T):
    for i,a in enumerate(pi):
      if arg_match(a, T):
        return i
    return None
  def get_comparison_hyper(self):
    global COMPARISON_FNS,LAST_GENERATED_COMPARISON_DOT_FN
    LAST_GENERATED_COMPARISON_DOT_FN=None
    hyper = ""
    if self._report.__class__==str or self._report.PI.__class__==int or self._report.PIP.__class__==int:
      return hyper
    fnds = plan_visualiser.create_dot(SCENARIO_POINTS,DOMAIN_INTERPRETATION.visualisation, OPERATOR_TEMPLATES, (list(map(lambda a: a, self._report.PI)), self._report.PIP), DEPTH)
    COMPARISON_FNS = fns = list(map(lambda fnd: ".".join(fnd.split(".")[:-1]), fnds))
    if LOCAL:
      for fn in fns:
        execute(["neato", "-Tpdf", "-o", fn + ".pdf", fn + ".dot"])
        if USE_HYPERLINKS:
          hyper +=  "\n<a href=\"" + fn + ".pdf\">Plan comparison figure</a>"
        elif OPEN_COMPARISON and OPEN_FIGS:
          open_pdf_t(fn+ ".pdf")
    LAST_GENERATED_COMPARISON_DOT_FN=fnds[0]
    return hyper

  def make_plan_dot(self):
    global LAST_GENERATED_PLAN_DOT_FN
    LAST_GENERATED_PLAN_DOT_FN=None
    if self._report.__class__==str or self._report.PIP.__class__==int:
      return
    PI = self._report.PIP
    LAST_GENERATED_PLAN_DOT_FN = plan_visualiser.create_dot(SCENARIO_POINTS,DOMAIN_INTERPRETATION.visualisation, OPERATOR_TEMPLATES, (list(map(lambda a: a, PI)),), DEPTH+1)[0]   
    

class bottom(constraint_component):
  def __init__(self): 
    super(bottom, self).__init__()
  def summary(self, spec):
    return "ORIGINAL"
QUERY_LIST.append((bottom(),[]))

class why_A_in_plan(constraint_component):
  spec_template=["A"]
  def __init__(self): 
    super(why_A_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    t = why_A_empirical.get_query_templates()[0]
    #for a in get_plan_actions(pi):
    a = random.choice(get_plan_actions(pi))
    if USE_NL:
      astr = _verbalise_action(a, td=False)
    else:
      astr = _a(a)
    d[tuple(a)] = t.replace("#A", astr)
    return d
  def is_ok_query(self, A, PI):
    plan_actions = get_plan_actions(PI)
    return not self.get_match_index(plan_actions, A) == None
  def add_component(self, A, M, PI, optic, depth):
    if self.is_ok_query(A, PI):
      pA = message_step_2_PlanAction((-1,A,0))
      self._report = why_A_empirical.why_A_Eff(optic, M, PI, pA, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, A)
    else:
      self._report = "Bad query parameter for A: "  + str(A)
    
  def test_component(self, pi, A):
    assert pi == None or self.get_match_index(pi, A) == None, "A matched at index: " + str(self.get_match_index(pi, A))
  def report(self):
    return super().report()
  def summary(self, A):
    return "NOT(" + A[0] + ")"
class why_not_A_in_plan(constraint_component):
  spec_template=["A"]
  def __init__(self): 
    super(why_not_A_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    t = why_not_A_empirical.get_query_templates()[0]
    a = random.choice(get_not_plan_actions(M, pi))
    #for a in get_not_plan_actions(M, pi):
    if USE_NL:
      astr = _verbalise_action(a, td=False)
    else:
      astr = _a(a)
    d[tuple(a)] = t.replace("#A", astr)
    return d
  def is_ok_query(self, A, M, PI):
    not_plan_actions = get_not_plan_actions(M, PI)
    return not self.get_match_index(not_plan_actions, A) == None
  def add_component(self, A, M, PI, optic, depth):
    if self.is_ok_query(A, M, PI):
      pA = message_step_2_PlanAction((-1,A,0))
      self._report = why_not_A_empirical.why_not_A(PI, pA, optic, M, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, A)
    else:
      self._report = "Bad query parameter for A: "  + str(A)
  def test_component(self, pi, A):
    assert pi == None or not self.get_match_index(pi, A) == None, "A not matched in plan, return of matcher: " + str(self.get_match_index(pi, A))
  def report(self):
    return super().report()
  def summary(self, A):
    return "DO(" + A[0] + ")"
class why_not_A_before_t_in_plan(constraint_component):
  spec_template=["A","Z"]
  def __init__(self): 
    super(why_not_A_before_t_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_not_A_before_t_empirical.get_query_templates()[0]
    pi_a = random.choice(pi)
    a = [pi_a.predicate] + pi_a.arguments
    mt = pi_a.time+pi_a.duration
    if mt < 2: return d
    t = random.randint(1, int(mt-1))
    if USE_NL:
      astr = _verbalise_action(a, td=False)
    else:
      astr = _a(a)
    d[(tuple(a),t)] = T.replace("#Z",str(t)).replace("#A", astr)
    return d
  def is_ok_query(self, spec, M, PI):
    A, t = spec
    for a in PI:
      if a.predicate == A[0] and arg_match(a.arguments, A[1:]):
        if a.time+a.duration < t:
          return False
    return True
  def add_component(self, spec, M, PI, optic, depth):
    A,t = spec
    if self.is_ok_query(spec, M, PI):
      pA = message_step_2_PlanAction((-1,A,0))
      self._report = why_not_A_before_t_empirical.why_not_A(PI, pA, t, optic, M, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      #if not pi == None:
      #  pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, spec)
    else:
      self._report = "Bad query parameter for A: "  + str(A)
  def test_component(self, pi, spec):
    if pi == None: return
    A,t = spec
    for a in pi:
      if a.predicate == A[0] and arg_match(a.arguments, A[1:]):
        assert a.time + a.duration <= t+1, "A not matched in plan before t.." 
        return
    assert False, "A not matched in plan"
  def report(self):
    return super().report()
  def summary(self, spec):
    (A,t) = spec
    return "Do<T(" + A[0] + ")"
class why_B_before_A_in_plan(constraint_component):
  spec_template=["A","A"]
  def __init__(self): 
    super(why_B_before_A_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    t = A_then_B_empirical.get_query_templates()[0]
    plan = get_plan_actions(pi)
    i = random.choice(range(len(plan)-1))
    j = random.choice(range(i+1, len(plan)))
    #for i in range(len(plan)-1):
    #  for j in range(i+1, len(plan)):
    k = tuple(plan[i]), tuple(plan[j])
    if USE_NL:
      astr = _verbalise_action(plan[j], td=False)
      bstr = _verbalise_action(plan[i], td=False)
    else:
      astr = _a(plan[j])
      bstr = _a(plan[i])
    d[k] = t.replace("#B", bstr).replace("#A", astr)
    return d
  def is_ok_query(self, spec, PI):
    (A, B) = spec
    plan_actions = get_plan_actions(PI)
    idA = self.get_match_index(plan_actions, A)
    idB = self.get_match_index(plan_actions, B)
    return not idA == None and not idB == None and idB < idA
  def add_component(self, spec, M, PI, optic, depth):
    (A, B) = spec
    if self.is_ok_query(spec, PI):  
      pA = message_step_2_PlanAction((-1,A,0))
      pB = message_step_2_PlanAction((-1,B,0))
      self._report = A_then_B_empirical.why_b_then_a(PI, pA, pB, optic, M, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if pi:
        self.test_component(list(map(lambda a: [a.predicate] + a.arguments, pi)), (A,B))
    else:
      self._report = "Bad query parameter for A: "  + str(A) + " or B: " + str(B)
  def test_component(self, pi, spec):
    if not pi == None:
      (A, B) = spec
      idxA = self.get_match_index(pi, A)
      idxB = self.get_match_index(pi, B)
      assert not idxB == None and not idxA == None and idxB > idxA
  def report(self):
    return super().report()
  def summary(self, spec):
    (A, B) = spec
    return "DO("+A[0] +";" +B[0] + ")"
class why_A_in_plan_causal(constraint_component):
  spec_template=["A"]
  def __init__(self): 
    super(why_A_in_plan_causal, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    t = causality.get_query_templates()[0]
    for a in get_plan_actions(pi):
      if USE_NL:
        astr = _verbalise_action(a, td=False)
      else:
        astr = _a(a)
      d[tuple(a)] = t.replace("#A", astr)
    return d
  def is_ok_query(self, A, PI):
    plan_actions = get_plan_actions(PI)
    return not self.get_match_index(plan_actions, A) == None
  def add_component(self, A, M, PI, optic, depth):
    global CAUSAL_GRAPH_DOT_FN
    
    CAUSAL_GRAPH_DOT_FN=None
    if self.is_ok_query(A, PI):
      pA = message_step_2_PlanAction((-1,A,0))
      self._report, fn = causality.why_a(M, PI, pA, LOCAL)
      if LOCAL:
        execute(["dot", "-Tpdf", "-o", fn + ".pdf", fn + ".dot"])
      self._fn=fn+".pdf"
      CAUSAL_GRAPH_DOT_FN=fn+".dot"
      if LOCAL and OPEN_FIGS and not USE_HYPERLINKS:
        open_pdf_t(self._fn)
    else:
      self._report = "Bad query parameter for A: "  + str(A)
      self._fn=None
  def report(self):
    hyper =  ""
    if not self._fn == None:
      hyper = "<a href=\"" + self._fn + "\">Causal analysis figure</a>"
    s = str(self._report) 
    if LOCAL and self._fn and USE_HYPERLINKS: 
      s += "\n" + hyper
    return s
class why_high_function_value_in_plan(constraint_component):
  spec_template=["F"]
  def __init__(self): 
    super(why_high_function_value_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_high_function_value.get_query_templates()[0]
    F = get_active_functions(M)
    if len(F) == 0:
      return {}
    for i in range(5):
      f = random.choice(F)
      v = why_high_function_value.get_current_metric_value(M, pi, [f.name]+f.args)
      if USE_NL:
        fstr = _verbalise_function(f)
      else:
        fstr = str(f)
      if v > 0:
        d[(f,)]=T.replace("#F",fstr)
    
    return d
  def is_ok_query(self, f, M):
    F = get_functions(M)
    return not self.get_match_index(F, f) == None
  def add_component(self, f, M, PI, optic, depth):
    if self.is_ok_query(f, M):
      self._report = why_high_function_value.why_high_fv(optic, M, PI, f, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth, reduction_perc={True:10,False:0}[REDUCE_FUNC_10PC])
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, f)
    else:
      self._report = "Bad query parameter for f: "  + str(f)
    
  def test_component(self, pi, f):
    #assert pi == None or self.get_match_index(pi, A) == None, "A matched at index: " + str(self.get_match_index(pi, A))
    pass
  def report(self):
    return super().report()
  def summary(self, F):
    return "REDUCE("+F[0]+ ")"
class why_high_function_value_in_plan_by_x(constraint_component):
  spec_template=["F","Z"]
  def __init__(self): 
    super(why_high_function_value_in_plan_by_x, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_high_function_value.get_query_templates()[0]
    F = get_active_functions(M)
    if len(F) == 0:
      return {}
    for i in range(5):
      f = random.choice(F)
      v = why_high_function_value.get_current_metric_value(M, pi, [f.name]+f.args)
      if USE_NL:
        fstr = _verbalise_function(f)
      else:
        fstr = str(f)
      if v > 0:
        d[(f,)]=T.replace("#F",fstr) + " by " + str(random.randint(1, 8)*10)
    
    return d
  def is_ok_query(self, f, M):
    F = get_functions(M)
    return not self.get_match_index(F, f) == None
  def add_component(self, F, M, PI, optic, depth):
    f,rv = F
    if self.is_ok_query(f, M):
      self._report = why_high_function_value.why_high_fv(optic, M, PI, f, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth, reduction_perc=rv)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, f)
    else:
      self._report = "Bad query parameter for f: "  + str(f)
    
  def test_component(self, pi, f):
    #assert pi == None or self.get_match_index(pi, A) == None, "A matched at index: " + str(self.get_match_index(pi, A))
    pass
  def report(self):
    return super().report()
  def summary(self, F):
    return "REDUCE("+F[0]+ ")"    
class minimise_function_value_in_plan(constraint_component):
  spec_template=["F"]
  def __init__(self): 
    super(minimise_function_value_in_plan, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_high_function_value_metric.get_query_templates()[0]
    F = get_active_functions(M)
    if len(F) == 0:
      return {}
    for i in range(5):
      f = random.choice(F)
      v = why_high_function_value.get_current_metric_value(M, pi, [f.name]+f.args)
      if USE_NL:
        fstr = _verbalise_function(f)
      else:
        fstr = str(f)
      if v > 0:
        d[(f,)]=T.replace("#F",fstr)
    return d
  def is_ok_query(self, f, M):
    F = get_functions(M)
    return not self.get_match_index(F, f) == None
  def add_component(self, f, M, PI, optic, depth):
    if self.is_ok_query(f, M):
      self._report = why_high_function_value_metric.why_high_fv(optic, M, PI, f, 0.999, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, f)
    else:
      self._report = "Bad query parameter for f: "  + str(f)
    
  def test_component(self, pi, f):
    pass # no indicator of success
  def report(self):
    return super().report()
  def summary(self, F):
    return "MINIMISE("+F[0]+ ")"
class minimise_add_function_in_plan(constraint_component):
  spec_template=["F","R"]
  def __init__(self): 
    super().__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_high_function_value_metric.get_query_templates()[1]
    F = get_active_functions(M)
    if len(F) == 0:
      return {}
    for i in range(5):
      f = random.choice(F)
      v = why_high_function_value.get_current_metric_value(M, pi, [f.name]+f.args)
      if USE_NL:
        fstr = _verbalise_function(f)
      else:
        fstr = str(f)
      if v > 0:
        d[(f,)]=T.replace("#F",fstr).replace("#R", "0.999")
    return d
  def is_ok_query(self, spec, M):
    f, n = spec
    n < 1.001
    F = get_functions(M)
    print (f, F)
    return not self.get_match_index(F, f) == None
  def add_component(self, spec, M, PI, optic, depth):
    if self.is_ok_query(spec, M):
      f, n = spec
      self._report = why_high_function_value_metric.why_high_fv(optic, M, PI, f, n, METRICS[depth], DOMAIN_INTERPRETATION, depth=depth)
      pi = get_current_plan(depth)
      if pi.__class__==int: pi = None
      if not pi == None:
        pi = list(map(lambda a: [a.predicate] + a.arguments, pi))
      self.test_component(pi, f)
    else:
      self._report = "Bad query parameter for f: "  + str(f)
    
  def test_component(self, pi, f):
    pass # no indicator of success
  def report(self):
    return super().report()
  def summary(self, spec):
    f, n = spec
    return "MINIMISE("+f[0]+ "["+str(n)+"])"    
class why_high_function_value_at_time(constraint_component):
  spec_template=["F","Z"]
  def __init__(self): 
    super(why_high_function_value_at_time, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    T = why_high_function_value_til.get_query_templates()[0]
    F = get_active_functions(M)
    max_t = int(max(map(lambda a: a.time + a.duration, pi)))
    if len(F) == 0:
      return {}
    for i in range(10):
      f = random.choice(F)
      t = random.randint(1, max_t)
      v = why_high_function_value_til.get_current_metric_value(M, pi, [f.name]+f.args, t)
      if USE_NL:
        fstr = _verbalise_function(f)
      else:
        fstr = str(f)
      if v > 0:
        d[(f,t)]=T.replace("#Z",str(t)).replace("#F",fstr)
    return d
  def is_ok_query(self, spec, PI, M):
    (f,t) = spec
    max_t = max(map(lambda a: a.time + a.duration, PI))
    F = get_functions(M)
    return not self.get_match_index(F, f) == None and isinstance(t, int) and t <= max_t
  def add_component(self, spec, M, PI, optic, depth):
    (f,t) = spec
    if self.is_ok_query((f,t), PI, M):
      if USE_NUMERIC_CONSTRAINT:
        self._report = why_high_function_value_til.why_high_fv(optic, M, PI, f, METRICS[depth], t, DOMAIN_INTERPRETATION, depth=depth, reduce_func_by_10pc=REDUCE_FUNC_10PC)
      else:
        print ("WARNING: not implemented metric version.. - probably not compatible..")
      new_pi = get_current_plan(depth)
      if new_pi.__class__==int: new_pi = None
      if new_pi == None:
        print ("No plan generated..")
      else:
        self.test_component(M, PI, new_pi, (f,t))
    else:
      self._report = "Bad query parameter for f/t: "  + str((f,t))
    
  def test_component(self, M, pi_0, pi_1, spec):
    (f,t) = spec
    assert why_high_function_value_til.test_constraint_satisfaction(f, t, pi_0, pi_1, M)
  def report(self):
    return super().report()
  def summary(self, spec):
    F,t = spec
    return "< at T("+F[0]+ ")"
class make_duration_near_function(constraint_component):
  spec_template=["O","O"]
  def __init__(self): 
    super(make_duration_near_function, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    dynamix = MAST.scenario_movers.get_movers()
    statix = MAST.scenario_points.get_points()
    T = model_extender.get_query_templates()[0]
    for i in range(5):
      o1 = random.choice(dynamix).get_name()
      o2 = random.choice(statix).get_name()
      d[tuple((o1,o2))] = T.replace("#O1", str(o1)).replace("#O2", str(o2))
    return d
  def is_ok_query(self, spec, PI):
    obj1, obj2 = spec
    return obj1 in MAST.scenario_movers and obj2 in MAST.scenario_points
  def add_component(self, spec, M, PI, optic, depth):
    global LAST_GENERATED_LANGUAGE_DOT_FN, POSSIBLE_QUERIES_USING_LANGUAGE
    LAST_GENERATED_LANGUAGE_DOT_FN = None
    POSSIBLE_QUERIES_USING_LANGUAGE=[]
    if self.is_ok_query(spec, PI):
      obj1, obj2 = spec
      self._report = model_extender.monitor_duration_near(obj1, obj2, M, PI, MAST, depth=depth)
      if not self._report.dot_fn == None:
        if LOCAL and OPEN_FIGS:
          execute(["neato", "-Tpdf", "-o", self._report.dot_fn + ".pdf", self._report.dot_fn + ".dot"])
          execute(["okular", self._report.dot_fn + ".pdf"])
        LAST_GENERATED_LANGUAGE_DOT_FN=self._report.dot_fn+".dot"
        templates = [why_high_function_value.get_query_templates()[0], why_high_function_value_metric.get_query_templates()[0]]
        POSSIBLE_QUERIES_USING_LANGUAGE += model_extender.propose_queries_to_use_duration_near(obj1, obj2, templates, MAST)
      self._report.V = get_function_value_sequence([self._report.f], DEPTH+1)
      return not self._report.dot_fn == None # True if a new extension was added
    else:
      self._report = "Bad query parameter for objects: "  + ", ".join(list(map(lambda x: str(x), spec)))
    
  def test_component(self, pi, A):
    assert pi == None or self.get_match_index(pi, A) == None, "A matched at index: " + str(self.get_match_index(pi, A))
  def report(self):
    return super().report()
  def summary(self, spec):
    obj1, obj2 = spec
    print (obj1, obj2)
    return "MONITOR("+obj1+"≈" +obj2 +")"

class make_total_distance_function(constraint_component):
  spec_template=["O"]
  def __init__(self): 
    super(make_total_distance_function, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    dynamix = MAST.scenario_movers.get_movers()
    T = model_extender.get_query_templates()[2]
    for i in range(1):
      o1 = random.choice(dynamix).get_name()
      d[o1] = T.replace("#O1", str(o1))
    return d
  def is_ok_query(self, spec, PI):
    obj1= spec
    return obj1 in MAST.scenario_movers
  def add_component(self, spec, M, PI, optic, depth):
    global POSSIBLE_QUERIES_USING_LANGUAGE
    POSSIBLE_QUERIES_USING_LANGUAGE=[]
    if self.is_ok_query(spec, PI):
      obj1 = spec
      self._report = model_extender.monitor_distance_travelled(obj1, M, PI, MAST, depth=depth)
      if self._report.is_new == True:
        templates = [why_high_function_value.get_query_templates()[0], why_high_function_value_metric.get_query_templates()[0]]
        POSSIBLE_QUERIES_USING_LANGUAGE += model_extender.propose_queries_to_use_distance_travelled(obj1, templates, MAST)
      self._report.V = get_function_value_sequence([self._report.f], DEPTH+1)
      return self._report.is_new
    else:
      self._report = "Bad query parameter for objects: " + str(spec)
    
  def test_component(self, pi, A):
    assert pi == None or self.get_match_index(pi, A) == None, "A matched at index: " + str(self.get_match_index(pi, A))
  def report(self):
    return super().report()
  def summary(self, obj1):
    print (obj1)
    return "DISTANCE("+obj1 +")"

class why_not_this_allocation(constraint_component):
  spec_template=["O","O*","O","O*"]
  def __init__(self): 
    super(why_not_this_allocation, self).__init__()
  def propose_components(self, M, pi):
    d = {}
    dynamix = MAST.scenario_movers.get_movers()
    tasks = MAST.get_tasks()[:]
    print (tasks, dynamix)
    T = MAST.get_rm_query_templates()[0]
    if len(dynamix) < 2: return d
    for i in range(1):
      assets = list(map(lambda x: x.get_name(), random.sample(dynamix, 2)))
      random.shuffle(tasks)
      allocation = {asset: [] for asset in assets}
      for i, task in enumerate(tasks):
        j = i % len(assets)
        asset = assets[j]
        allocation[asset].append(task)
      tup=tuple()
      for j, asset in enumerate (assets):
        T = T.replace("#O" + str(j)+"*", say_list(allocation[asset]))
        T = T.replace("#O" + str(j), str(asset))
        tup += (asset, tuple(allocation[asset]))
      d[tup] = T
    return d
  def is_ok_query(self, spec, PI):
    obj1, l1, obj2, l2 = spec
    O = MAST.scenario_movers.keys()
    return obj1 in O and obj2 in O
  def add_component(self, spec, M, PI, optic, depth):
    global POSSIBLE_QUERIES_USING_LANGUAGE
    POSSIBLE_QUERIES_USING_LANGUAGE=[]
    if self.is_ok_query(spec, PI):
      obj1, ra1, obj2, ra2 = spec
      self._report = MAST.force_allocation(obj1, ra1, obj2, ra2, M, PI, METRICS[depth], DOMAIN_INTERPRETATION, depth)
    else:
      self._report = "Bad query parameters.."
  def test_component(self, PI, spec):
    assert True
  def report(self):
    return super().report()
  def summary(self, spec):
    obj1, l1, obj2, l2 = spec
    return "ALLOCATE("+obj1 +"_&_" + obj2 +")"



constraint_component_map = {"why A? [Empirical]": why_A_in_plan,
                            "why not A? [Empirical]": why_not_A_in_plan,
                            "why B then A? [Empirical]": why_B_before_A_in_plan,
                            "why A? [Causal]": why_A_in_plan_causal,
                            "why f high? [Empirical]": why_high_function_value_in_plan,
                            "why f high at t? [Empirical]": why_high_function_value_at_time,
                            "minimise f [Empirical]" : minimise_function_value_in_plan,
                            "minimise f with weight [Empirical]": minimise_add_function_in_plan,
                            "monitor duration o1 near o2 [Extension]": make_duration_near_function,
                            "monitor total distance of o1 [Extension]": make_total_distance_function,
                            "why not A pre t? [Empirical]" : why_not_A_before_t_in_plan,
                            "why f high by X? [Empirical]" : why_high_function_value_in_plan_by_x,
                            "why not this allocation? [Empirical]": why_not_this_allocation
                            }
constraint_components_index = dict(zip(range(len(constraint_component_map)),sorted(constraint_component_map.keys())))


class constraint_message:
  def __init__(self, constraint_type, depth, PI, A, args = {}, B = None):  
    self.constraint_type = constraint_type
    self.depth = depth
    self.PI = PI
    self.A = A
    self.B = B
    self.args = args

def gather_values(lst):
  result = []
  current_value = lst[0]
  for value in lst:
    if value[0] != current_value[0]:
      result.append(current_value)
      current_value = value
  result.append(current_value)
  return result

def get_function_value_sequence(f_l, depth):
  M, PI, _ = load_existing_model(depth)
  S = simulator.get_states_sequence(M, PI)
  V = []
  for s in S:
    V.append((s.funcs[planning_types.Proposition(f_l[0], f_l[1:])],s.funcs[planning_types.Proposition("total-time", [])]))
  V = gather_values(V)
  return V

def _htmlise(s):
  return s.replace("\n","<br>")

def _test_html(s):
  fn = "_report_out.html"; f=open(fn,"w"); f.write(s); f.close()
  execute(["firefox", fn])

def message_step_2_PlanAction(e):
  (t,ma,d) = e
  return planning_types.PlanAction(float(t), ma[0], ma[1:], int(d))
  
def get_plan(message_PI):
  return list(map(lambda ma: message_step_2_PlanAction(ma), message_PI))

def get_planner(dfn, pfn):
  M = model_loader.get_planning_model(dfn, pfn)
  optic = planner.planner(dfn, M[0], M[1], M[1].goal, True)
  return M, optic

def get_all_queries():
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  M, PI, optic = load_existing_model(DEPTH)
  q_m = {}
  for constraint_component in constraint_component_map.values():
    try:
      cci = constraint_component()
      q_m[cci] = cci.propose_components(M, PI)
    except Exception as e:
      traceback.print_exc()
      print ("Failed to generate constraint proposal for type: " + str(constraint_component) + ", continuing..")
  del M, PI, optic
  return q_m

def get_possible_planning_actions(depth):
  M, PI, optic = load_existing_model(depth)
  return get_all_actions(M)

def get_planning_actions_in_plan(depth):
  M, PI, optic = load_existing_model(depth)
  return get_plan_actions(PI)

def get_planning_actions_not_in_plan(depth):
  M, PI, optic = load_existing_model(depth)
  return get_not_plan_actions(M, PI)

def get_current_plan(depth):
  M_TAG = get_M_Tag(depth)
  try:
    PI = plan_parser.parse_plan(open(get_plan_path(M_TAG)).read())
    return PI
  except: pass

def is_system_initialised():
  return DEPTH >= 0
def check_is_initialised():
  assert DEPTH >= 0, "System not initialised."

def _verbalise_plan(PI):
  if PI == None:
    return "I have no current plan."
  return "".join(map(lambda t: "  * " + t + "\n", verbaliser.verbalise(PI, DOMAIN_INTERPRETATION, OPERATOR_TEMPLATES)))

def _verbalise_current_plan():
  PI = get_current_plan(DEPTH)
  return _verbalise_plan(PI)

def _verbalise_action(a, td=False):
  if a.__class__ == list:
    a = message_step_2_PlanAction((-1, a, 0))
  return verbaliser.verbalise([a], DOMAIN_INTERPRETATION, OPERATOR_TEMPLATES, td=td)[0]

def _verbalise_function(f):
  return verbaliser.verbalise_function(f, FUNCTION_TEMPLATES)


def set_planner_timeout(t):
  try:
    set_planner_time_limit(int(t))
    return "Planner timeout set to " + str(t)
  except:
    pass
  return "Nothing happend for timeout=", str(t)

def _get_plan_str():
  return plan_printer(get_current_plan(DEPTH)) +"\n"

def get_constraints_str(d):
  # ("->".join(map(lambda x: str(x), range(d))))
  l=[]
  for i in range(d+1):
    c,spec = QUERY_LIST[i]
    l.append("["+str(i)+"] " + c.summary(spec))
  return " -> ".join(l)



def get_plan_str(fig=True):
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  cs = get_constraints_str(DEPTH)
  s = "Constraint levels: " + cs +"\n"
  s += "<strong>Here's my current plan:</strong>\n"
  if USE_NL:
    s += _verbalise_current_plan()
  else:
    s += _get_plan_str()
  # make plan pic
  if LOCAL and fig:
    PI = get_current_plan(DEPTH)
    fnd = plan_visualiser.create_dot(SCENARIO_POINTS,DOMAIN_INTERPRETATION.visualisation, OPERATOR_TEMPLATES, (list(map(lambda a: a, PI)),), DEPTH)[0]
    fn = ".".join(fnd.split(".")[:-1])
    execute(["neato", "-Tpdf", "-o", fn + ".pdf", fn + ".dot"])
    if USE_HYPERLINKS:
      s +=  "\n<a href=\"" + fn + ".pdf\">Plan comparison figure</a>"
    elif OPEN_FIGS:
      open_pdf_t(fn+ ".pdf")
    
  if USE_HTML:
    s= _htmlise(s)
  if TEST_HTML:
    _test_html(s)
  return s

def examine_previous_comparison():
  if LOCAL:
    for fn in COMPARISON_FNS:
      open_pdf_t(fn + ".pdf")
  else:
    return get_comparison_dot_str()

def parse_spec_param(param, kind, M):
  print ("**** Param: ", param, "as kind", kind)
  v = param
  try:
    if kind == "A":
      if USE_NL:
        v = nl2action.match_action(param, OPERATOR_TEMPLATES)[0]  
    elif kind == "O":
      O = list(MAST.scenario_movers.keys()) + list(MAST.scenario_points.keys())
      v = nl2action.match_object(param, O)
    elif kind == "O*":
      v = tuple(read_list(param))
    elif kind == "F":
      if USE_NL:
        #v = nl2action.match_function(param, FUNCTION_TEMPLATES)[0]
        v = function_finder.get_function(param, FUNCTION_TEMPLATES, [MAST])[0]
    elif kind == int:
      v = int(param)
  except Exception as e:
    traceback.print_exc()
    print ("WARNING: tried to parse param: ", param, "as kind", kind, "(FAILED)", type(e), e)
  print ("Parameter parsed as: ", v)
  return v

# spec = A, or (A,B) depending on type!?
def plan_query(query_type, spec):
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  if not query_type in constraint_component_map:
    return "Failed to query plan with unknown type: " + str(query_type)
  remove_model_layer(DEPTH+1)
  constraint_component = constraint_component_map[query_type]
  try:
    M, PI, optic = load_existing_model(DEPTH)
  except Exception as e: 
    traceback.print_exc()
    return "Failed to load existing model in xaip_toolkit at depth " + str(DEPTH) +"\n" + str(e)
  if PI == None:
    return "No existing plan to load in xaip_toolkit at depth " + str(DEPTH)
  query_params=[]
  if len(constraint_component.spec_template)==1:
    spec = [spec]
  info = "Parsing arguments for query type: " + str(query_type) + "\n"
  for (param, kind) in zip(spec, constraint_component.spec_template):
    info += "Attempting to parse " + str(param) + ", as kind " + str(kind) + "...\n"
    try:
      query_params.append(parse_spec_param(param, kind, M))
    except Exception as e:
      traceback.print_exc()
      return "Failed to parse argument. So far I tried the following:\n" + info + "Then error in xaip_toolkit at depth " + str(DEPTH) +"\n" + str(e)
    info += "Parsed as " + str(query_params[-1]) + "\n"
  METRICS[DEPTH+1] = METRICS[DEPTH][:]
  if len(constraint_component.spec_template)==1:
    query_params = query_params[0]
  print ("ADDING CONSTRAINT TO MODEL...")
  
  try:
    shutil.copyfile(temp_fs_path + "/_function_templates_"+str(DEPTH)+".yaml", temp_fs_path + "/_function_templates_"+str(DEPTH+1)+".yaml")
  except Exception as e: 
    traceback.print_exc()
    return "Failed to copy function templates in xaip_toolkit at depth " + str(DEPTH) +"\n" + str(e)
  
  try: # we can have added to the model during parsing parameters..
    M, PI, optic = load_existing_model(DEPTH)
  except Exception as e: 
    traceback.print_exc()
    return "Failed to load existing model in xaip_toolkit at depth " + str(DEPTH) +"\n" + str(e)
  
  constraint_component_inst = constraint_component()
  try:
    auto_accept = constraint_component_inst.add_component(query_params, M, PI, optic, DEPTH+1)
  except Exception as e: 
    traceback.print_exc()
    return "Failed to add constraint of type " + str(query_type) + " with parameters: " + str(query_params) + " in xaip_toolkit at depth " + str(DEPTH) +"\n" + str(e)
  print ("CONSTRAINT ADDED...", DEPTH)
  try: QUERY_LIST[DEPTH+1] = (constraint_component_inst, query_params)
  except: QUERY_LIST.append((constraint_component_inst, query_params))
  if auto_accept:
    user_agrees_with_new_plan()
  
  report = constraint_component_inst.report()
  if USE_HTML:
    report = _htmlise(report)
  if TEST_HTML:
    _test_html(report)
  return report

def user_does_not_agree_with_new_plan():
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  return True

def user_agrees_with_new_plan():
  global DEPTH
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  if check_next_layer_exists():
    DEPTH+=1
    load_function_templates()
    return True
  return False

def check_next_layer_exists():
  M_TAG = get_M_Tag(DEPTH+1)
  dfn, pfn = get_new_model_paths(M_TAG)
  pifn = get_plan_path(M_TAG)
  for fn in (dfn, pfn, pifn):
    if not os.path.exists(fn):
      return False
  return True

def move_up_a_level():
  global DEPTH
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  if DEPTH > 0:
    DEPTH-=1
    remove_model_layer(DEPTH+1)
    load_function_templates()
    return True
  return False

def return_to_the_initial_plan():
  global DEPTH
  if not is_system_initialised():
    return "XAIP is not initialised - please initialise before running commands.."
  for i in range(1,DEPTH+1):
    remove_model_layer(i)
  DEPTH=0
  load_function_templates()
  return True

def remove_model_layer(depth):
  M_TAG = get_M_Tag(depth)
  dfn, pfn = get_new_model_paths(M_TAG)
  pifn = get_plan_path(M_TAG)
  b=False
  print ("Removing model layer...", depth, end=" ")
  for mfn in (dfn, pfn, pifn):
    try:
      os.remove(mfn)
      b=True
    except:
      pass
  print ("Found files")
  return b

def _get_sample_queries():
  qs = get_all_queries()
  s = ""
  try:
    for k in qs:
      if len(qs[k].values()) > 0:
        v = list(qs[k].values())[0]
        s += "  * " + str(v) + "\n"
    return s
  except:
    return qs

def get_sample_queries_list():
  qs = get_all_queries()
  try:
    l = []
    for k in qs:
      if len(qs[k].values()) > 0:
        v = list(qs[k].values())[0]
        l.append(v)
    return l
  except:
    return qs

def get_sample_queries():
  s = _get_sample_queries()
  if USE_HTML:
    s= _htmlise(s)
  if TEST_HTML:
    _test_html(s)
  return s

def get_objects_of_type(objmap, t):
  return list(map(lambda e: e[0], filter(lambda e: e[1]==t, objmap.items())))

def get_model_str():
  M, PI, optic = load_existing_model(DEPTH)
  s = "The planning model for the trial called: " + M[1].name + ",\n has " + str(len(M[0].actions)) + " planning operators:\n * " + " * ".join(map(lambda x: x.name + "\n",M[0].actions))+""
  s += "There are a total of " + str(len(M[2])) + " ground actions, e.g., " + just_action_str(M[2][0])+ ".\n"
  objmap = M[1].objects
  types = set(objmap.values())
  for t in types:
    tobj = get_objects_of_type(objmap, t)
    s += "The model has " + str(len(tobj)) + " object(s) of type: " + str(t) +".\n"
  s += "There are also " + str(len(M[1].goal.conj)) + " goals:\n" + str(M[1].goal)
  return s
      
    
    

def generate_initial_text(model_info=True):
  if model_info:
    s = get_model_str()
  else:
    s = ""
  s += "\n========================================\n\n"
  #s += get_plan_str(fig=False)
  s += "<strong>Do you have any queries?</strong> For example, here are some examples:\n"
  s += _get_sample_queries()
  return s

def implement_sys_settings (sysd):
  print (sysd)
  OR.OPTIC_PLANNER_COMMAND = sysd["planner_path"]
  planning_helper.MONITOR_OPTIC = sysd["monitor_optic"]
  if "timeout" in sysd:
    set_planner_timeout(int(sysd["timeout"]))
  

def load_and_implement_sys_settings(sys_settings_fn):
  f = open(sys_settings_fn, 'r')
  d = yaml.safe_load(f)
  sysd = d["Settings"]["System"]
  implement_sys_settings (sysd)

def load_function_templates():
  global FUNCTION_TEMPLATES
  M, _, _ = load_existing_model(DEPTH)
  FUNCTION_TEMPLATES = template_loader.parse_action_templates(temp_fs_path + "/_function_templates_" + str(DEPTH) +".yaml", M[0].functions, M)
def load_operator_templates():
  global OPERATOR_TEMPLATES
  M, _, _ = load_existing_model(DEPTH)
  OPERATOR_TEMPLATES = template_loader.parse_action_templates(temp_fs_path + "/_operator_templates_0.yaml", M[0].actions, M)

def init_nl_support_files():
  ot = DOMAIN_INTERPRETATION.nl["operator_templates"]  
  ft = DOMAIN_INTERPRETATION.nl["function_templates"]
  shutil.copyfile(parent_directory+"/"+ot, temp_fs_path + "/_operator_templates_0.yaml")
  shutil.copyfile(parent_directory+"/"+ft, temp_fs_path + "/_function_templates_0.yaml")

def init_from_fns(d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn, nl=True):
  global DEPTH,USE_NL,initialised,MODEL_DOT_FN,SCENARIO_POINTS,DOMAIN_INTERPRETATION
  if initialised:
    print ("WARNING: XAIP toolkit already initialised.")
    return "WARNING: XAIP toolkit already initialised."
  M_TAG = get_M_Tag(0)
  
  # init globals
  USE_NL=nl
  DEPTH = 0

  SCENARIO_POINTS = scenario_points_loader.load_points(p_interp_fn)
  DOMAIN_INTERPRETATION = interpretation_loader.load_interpretations(d_interp_fn)
  load_and_implement_sys_settings(sys_settings_fn)

  if LOCAL: 
    m = plan_visualiser.set_graph_scale(SCENARIO_POINTS)
    #mast.MULT = m
  #mast.NEAR = scenario_points.near

  fs_init()

  ndfn, npfn = get_new_model_paths(M_TAG)
  try:
    for (src, dst) in ((d_fn, ndfn), (p_fn, npfn)):
      shutil.copyfile(src, dst)
  except Exception as e: 
    traceback.print_exc()
    return "Failed to move initial model files into position.\n" + str(e)
  try:
    init_nl_support_files()
    load_function_templates()
    load_operator_templates()
  except Exception as e: 
    traceback.print_exc()
    return "Failed to move initial function_templates.yaml file into position.\n" + str(e)
  
  # prepare the mission dot graph
  try:
    MODEL_DOT_FN=fnd = plan_visualiser.create_structure_dot(SCENARIO_POINTS, DOMAIN_INTERPRETATION.visualisation)
    if LOCAL:
      fn = ".".join(fnd.split(".")[:-1])
      execute(["neato", "-Tpdf", "-o", fn + ".pdf", fn + ".dot"])
      if OPEN_FIGS:
        open_pdf_t(fn+ ".pdf")
  except Exception as e: 
    traceback.print_exc()
    print( "Failed to make initial mission DOT...\n" + str(e) + "\nContinuing...")
  return init_plan_and_mast()
  
  
def init_plan_and_mast(model_info=True):
  global DEPTH,initialised,LAST_GENERATED_PLAN_DOT_FN,MAST,RUN_TUPLE

  M_TAG = get_M_Tag(0)
  
  
  try:
    PI = abstraction.make_abs_plan(0, DOMAIN_INTERPRETATION)
  except Exception as e: 
    traceback.print_exc()
    return ( "Exception during planning for initial model...\n" + str(e))

  if PI:
    try:
      M, _, _ = load_existing_model(0)
      RUN_TUPLE = (M[0].name,M[1].name)
    except Exception as e: 
      traceback.print_exc()
      return ( "Failed to load initial model.\n" + str(e))
      
    try: 
      MAST = mast.MAST_builder(M, SCENARIO_POINTS, DOMAIN_INTERPRETATION, 1)
      MAST.init(M)
    except Exception as e:
      traceback.print_exc()
      MAST = None
      return ( "Failed to initialise MAST interpretation of model...\n" + str(e))
    
    if not PI.__class__==int:
      LAST_GENERATED_PLAN_DOT_FN = plan_visualiser.create_dot(SCENARIO_POINTS, DOMAIN_INTERPRETATION.visualisation, OPERATOR_TEMPLATES, (list(map(lambda a: a, PI)),), 0)[0]
    initialised = True
    try:
      return generate_initial_text(model_info)  
    except Exception as e: 
      traceback.print_exc()
      return ( "Failed to generate initial message to the user.. so hi! ;)\n" + str(e))
    
  DEPTH=-1
  return "WARNING: XAIP toolkit failed to initialise - planner failed to generate initial plan..."


def get_query_templates():
  templates = []
  """producers = [("why A? [Empirical]",(why_A_empirical)),
               ("why not A? [Empirical]", why_not_A_empirical), 
               ("why B then A? [Empirical]", A_then_B_empirical),
               ("why A? [Causal]", causality)] """
  for k,producer in constraint_component_map:
    templates += list(map(lambda x: (k,x), producer().get_query_templates()))
  return templates

def interactive_from_files(d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn):
  s = init_from_fns(d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn)  
  print (s)
  if s.startswith("WARNING"):
    print ("***************** Exiting!")
    sys.exit(1)
  interactive()

def interactive():
  import tracemalloc
  tracemalloc.start()
   
  PARAM_TO_FORMAT = {"A": lambda e: e.split(" "), "O": lambda e: e.split(" "), "O*": str, "F": lambda e: e.split(" "), "Z": int, "R": float}
  add_opts = ["get a plan string", "get sample queries", "get previous comparison", "set planner timeout", 
                 "get function valuation", "get resource allocations", "reset system"]
  add_opts_d = dict(zip(range(len(constraint_components_index), len(constraint_components_index)+len(add_opts)),add_opts))
  OPTIONS = {**constraint_components_index, **add_opts_d}
  for i, c in OPTIONS.items():
    print ("*", i, c)
  print ("* 'exit' to quit..")
  
  KEEP_GOING=True
  while KEEP_GOING:
    snapshot1 = tracemalloc.take_snapshot()
    print ("Enter a query, or exit to stop:")
    q = input().strip()
    if q == "exit":
      KEEP_GOING = False
    else:
      bits = q.split("@")
      mode = int(bits[0])
      if mode in OPTIONS:
        opt = OPTIONS[mode]
        if mode in constraint_components_index:
          query_type = constraint_components_index[mode]
          typs = constraint_component_map[query_type].spec_template
          params = []
          for (e,t) in zip(bits[1:], typs):
            params.append(PARAM_TO_FORMAT[t](e))
          if len(typs) == 1:
            print(plan_query(query_type, params[0]))
          else:
            print(plan_query(query_type, params))
          if query_type == "why A? [Causal]": continue
          print ("Keep this new plan? y/n/o/u")
          r = input().strip()
          if r=="y":
            user_agrees_with_new_plan()
          elif r == "o":
            return_to_the_initial_plan()
          elif r == "u":
            move_up_a_level()
          else:
            user_does_not_agree_with_new_plan()
        else: 
          if opt=="get a plan string":
            print (get_plan_str()) ## XXX 
          elif opt == "get sample queries":
            print (get_sample_queries())
          elif opt == "get previous comparison":
            examine_previous_comparison()
          elif opt == "reset system": 
            print ("WARNING: Not currently implemented!")
          elif opt == "set planner timeout":
            print (set_planner_timeout(int(bits[1])))
          elif opt == "get function valuation":
            M, PI, _ = load_existing_model(DEPTH)
            v = nl2action.match_function(bits[1].split(" "), FUNCTION_TEMPLATES)[0]
            V=get_function_value_sequence(v, DEPTH)
            if V == None: print ("Nothing to show...")
            else: 
              print ("\nIn the current plan the function has values:\n  " + "\n  ".join(map(lambda v: "["+str(v[1])+"] " + str(v[0]),V)))
          elif opt == "get resource allocations":
            _, PI, _ = load_existing_model(DEPTH)
            print(MAST.get_allocation(PI))
      else:
        print ("Unknown option: ", mode)
        for i, c in OPTIONS.items():
          print ("*", i, c)
        print ("* 'exit' to quit..")
    snapshot2 = tracemalloc.take_snapshot()
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("[ Top 10 differences ]")
    for stat in top_stats[:10]:
      print(stat)
    current, peak = tracemalloc.get_traced_memory()
    print(f"Run: Current memory usage: {current / 10**6:.4f} MB; Peak: {peak / 10**6:.4f} MB")
    for e in POSSIBLE_QUERIES_USING_LANGUAGE + get_sample_queries_list():
      print ("  **", e)
  tracemalloc.stop()
  

