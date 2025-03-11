import sys

from ..planning import pddl_io
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *
from . import constraint_support
from ..abstraction import abstraction_fe as abstraction



def make_FSM_state(M, M_TAG):
  pred_sym = "progress_marker_" + M_TAG+ "1"
  p = planning_types.ParameterList(pred_sym)
  M[0].predicates.append(p)
  return pred_sym

def add_effect(ops, Psym):
  p = planning_types.Predicate(Psym)
  list(map(lambda op: op.at_end_e.append(planning_types.PropAssign(p)), ops))

def add_constraint_to_action(a, Psym, M):
  p = planning_types.Proposition(Psym, list())
  a.at_start_c.append(planning_types.PropGoal(p))

def get_til_preds(M, M_TAG):
  pred_sym1 = "til_window" + M_TAG
  pred_sym2 = "sat_constraints" + M_TAG
  for pred_sym in pred_sym1, pred_sym2:
    p = planning_types.ParameterList(pred_sym)
    M[0].predicates.append(p)
  return pred_sym1, pred_sym2

def make_constraint_sat_action(t, M, M_TAG):
  wpsym, gpsym = get_til_preds(M, M_TAG)
  wp = planning_types.Proposition(wpsym, [])
  gp = planning_types.Proposition(gpsym, [])
  M[1].initial_state.tils.append(planning_types.TIL(t, planning_types.PropAssign(wp)))
  M[1].initial_state.tils.append(planning_types.TIL(t+0.1, planning_types.NegPropAssign(wp)))
  a = planning_types.DurativeAction("constraint_satisfier" + M_TAG + "z")
  a.duration = planning_types.Duration(planning_types.CalcNodeValue(1))
  a.at_start_c.append(planning_types.PropGoal(planning_types.Predicate(wp.name)))
  a.at_end_e.append(planning_types.PropAssign(planning_types.Predicate(gp.name)))
  M[0].actions.append(a)
  M[1].goal.conj.append(planning_types.PropGoal(planning_types.Proposition(gp.name, [])))
  return a

def insist_on_a_pre_t(A, t, M, M_TAG):
  Psym = make_FSM_state(M, M_TAG) 
  ops_A,ops_rest = constraint_support.split_op_by_action(op(A,M), A, M, M_TAG)
  add_effect(ops_A, Psym)
  ca = make_constraint_sat_action(t, M, M_TAG)
  add_constraint_to_action(ca, Psym, M)

class Not_A_pre_t_comparison(plan_comparison):  
  def __init__(self, A, t, PI, M, metrics):
    super(Not_A_pre_t_comparison, self).__init__(PI, M, metrics)
    self.A = A
    self.t = t
  def get_query(self):
    return "A (" + just_action_str(self.A) + ") not before time t (" + str(self.t) + ")"
  def get_dont_do_it(self):
    return "force A before t"

def why_not_A(PI, A, t, optic1, M, metrics, DOMAIN_INTERPRETATION, depth):
  M_TAG = get_M_Tag(depth)
  comparison = Not_A_pre_t_comparison(A, t, PI, M, metrics)
  insist_on_a_pre_t(A, t, M, M_TAG)
  
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison

def get_query_templates():
  return ["Why not #A before the time #Z?",]
      


