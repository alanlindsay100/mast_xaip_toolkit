import re, yaml

from .. import xaip_util
from ..interpretations import interpretation_loader
from ..pddl_resources import original_model_loader as model_loader
from ..planning import planner, optic_runner as OR, planning_helper
from . import move_action_abstraction as MAA


def solve_problem(ab_d_fn, ab_p_fn):
  abM, optic = load_model(ab_d_fn, ab_p_fn)
  return run_planner(optic, abM[1].initial_state, code_ret=True)

def do_abstract_planning(M, depth, DOMAIN_INTERPRETATION):
  maa = MAA.RestrictedMoveActionAbstraction(M, DOMAIN_INTERPRETATION)
  ab_d_fn, ab_p_fn = maa.make_abstract_model(depth)
  abPI = solve_problem(ab_d_fn, ab_p_fn)
  if abPI.__class__==int:
    PI = abPI
  else:
    PI = maa.de_abstract_plan(abPI)
    print ("<<<<<< Abstract plan length:", len(abPI), "; Expanded plan:", len(PI))
  return PI

def do_normal_planning(depth):
  M_TAG = xaip_util.get_M_Tag(depth)
  ndfn, npfn = xaip_util.get_new_model_paths(M_TAG)
  return solve_problem(ndfn, npfn)

def make_abs_plan(depth, DOMAIN_INTERPRETATION):
  if DOMAIN_INTERPRETATION.abstraction and DOMAIN_INTERPRETATION.abstraction["apply"]:
    M, _, _ = xaip_util.load_existing_model(depth)
    PI = do_abstract_planning(M, depth, DOMAIN_INTERPRETATION)
  else:
    PI = do_normal_planning(depth)
  if not PI.__class__==int:
    s = "\n".join(map(lambda a: str(a), PI))
    open(xaip_util.get_plan_path(xaip_util.get_M_Tag(depth)), 'w').write(s)
  return PI
  
def load_model(d_fn, p_fn):
  M = model_loader.get_planning_model(d_fn, p_fn)
  for a in M[0].actions:
    a.name = re.sub(r'\d+$', '', a.name)
  optic = planner.planner(d_fn, M[0], M[1], M[1].goal, True)
  M += (optic.get_optic_actions(M[1].initial_state, time_limit=xaip_util.PLANNING_TIME_LIMIT, client=not xaip_util.LOCAL),)
  for a in M[2]:
    a.predicate = re.sub(r'\d+$', '', a.predicate)
  return M, optic

def run_planner(planner, s, code_ret=False):
  return planner.do_optic(s, time_limit=xaip_util.PLANNING_TIME_LIMIT, code_ret=code_ret, client=not xaip_util.LOCAL)

def implement_sys_settings (sysd):
  print (sysd)
  OR.OPTIC_PLANNER_COMMAND = sysd["planner_path"]
  planning_helper.MONITOR_OPTIC = sysd["monitor_optic"]
  

def load_and_implement_sys_settings(sys_settings_fn):
  f = open(sys_settings_fn, 'r')
  d = yaml.safe_load(f)
  sysd = d["Settings"]["System"]
  implement_sys_settings (sysd)

def abstract(d_fn, p_fn, d_interp_fn, sys_settings_fn):
  load_and_implement_sys_settings(sys_settings_fn)
  DOMAIN_INTERPRETATION = interpretation_loader.load_interpretations(d_interp_fn)
  M, _ = load_model(d_fn, p_fn)
  PI = do_abstract_planning(M, 0, DOMAIN_INTERPRETATION)
  for a in PI:
    print (a)
  
