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

def insist_on_a(A, M, M_TAG):
  Psym = make_FSM_state(M, M_TAG)
  ops_A,ops_rest = constraint_support.split_op_by_action(op(A,M), A, M, M_TAG)
  constraint_support.add_effect(ops_A, Psym)
  constraint_support.add_fact_to_goal(M, Psym)

class Not_A_comparison(plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(Not_A_comparison, self).__init__(PI, M, metrics)
    self.A = spec
  def get_query(self):
    return "A (" + just_action_str(self.A) + ") not"
  def get_dont_do_it(self):
    return "force A"

def why_not_A(PI, A, optic1, M, metrics, DOMAIN_INTERPRETATION, depth):
  M_TAG = get_M_Tag(depth)
  comparison = Not_A_comparison(A, PI, M, metrics)
  insist_on_a(A, M, M_TAG)
  
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison

def get_query_templates():
  return ["Why not #A?",]
      


