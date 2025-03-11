
import sys

from ..planning import pddl_io
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *
from . import constraint_support
from ..abstraction import abstraction_fe as abstraction


class A_comparison(plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(A_comparison, self).__init__(PI, M, metrics)
    self.A = spec
  def get_query(self):
    return "A (" + just_action_str(self.A) + ")"
  def get_dont_do_it(self):
    return "miss the action"

def insist_on_not_A(A, M, M_TAG):
  ops_A,ops_nA = constraint_support.split_op_by_action(op(A,M), A, M, M_TAG)
  for o in ops_A:
    M[0].actions.remove(o)

"""
Make an explanation of why A is in the plan, by comparing it to a plan without A
"""
def why_A_Eff(optic1, M, PI, A, metrics, DOMAIN_INTERPRETATION, depth):
  M_TAG = get_M_Tag(depth)
  comparison = A_comparison(A, PI, M, metrics)
  
  insist_on_not_A(A, M, M_TAG)
  
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison
  
def get_query_templates():
  return ["Why #A?",]




