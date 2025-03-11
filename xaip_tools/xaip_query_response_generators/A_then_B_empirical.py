import sys

from ..planning import pddl_io
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *
from . import constraint_support
from ..abstraction import abstraction_fe as abstraction

"""
We want:
make P, add P to A.eff
=> split A.op into A and not A
add P to B.prec and Q to B.eff
=> split B.op into B and not B
[add Q as goal] depending on interpretation (command line option)
"""

def make_FSM_states(M, M_TAG):
  syms = "progress_marker_" + M_TAG+ "1", "progress_marker_" + M_TAG+ "2"
  for pred_sym in syms:
    p = planning_types.ParameterList(pred_sym)
    M[0].predicates.append(p)
  return syms

def insist_on_a_then_b(A, B, M, M_TAG, force_B=True):
  Psym,Qsym = make_FSM_states(M, M_TAG)
  ops_A,ops_rest = constraint_support.split_op_by_action(op(A,M), A, M, "pa_"+M_TAG)
  if A.predicate == B.predicate :
    ops_B,ops_B_rest = constraint_support.split_op_by_action(ops_rest, B, M, "pb_"+M_TAG)
  else:
    ops_B,ops_B_rest = constraint_support.split_op_by_action(op(B,M), B, M, "pb_"+M_TAG)
    
  constraint_support.add_effect(ops_A, Psym)
  constraint_support.add_precondition(ops_B, Psym)
  constraint_support.add_effect(ops_B, Qsym)
  
  if force_B:
    constraint_support.add_fact_to_goal(M, Qsym)

class A_then_B_comparison(plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(A_then_B_comparison, self).__init__(PI, M, metrics)
    self.A, self.B = spec
  def get_query(self):
    return "B (" + just_action_str(self.B) + ") before A (" + just_action_str(self.A) + ")"
  def get_dont_do_it(self):
    return "force A then B"

def why_b_then_a(PI, A, B, optic1, M, metrics, DOMAIN_INTERPRETATION, depth, force_B=True):
  M_TAG = get_M_Tag(depth)
  comparison = A_then_B_comparison((A,B), PI, M, metrics)
  insist_on_a_then_b(A, B, M, M_TAG, force_B)
  
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison

def get_query_templates():
  return ["Why #B before #A?",]
      
if __name__ == '__main__':
  import lpg_parser as plan_parser

  domain_path, problem_path = sys.argv[1:3]

  M = model_loader.get_planning_model(domain_path, problem_path)
  optic = planner.planner(domain_path, M[0], M[1], M[1].goal, True)
  M += (optic.get_optic_actions(M[1].initial_state, time_limit=PLANNING_TIME_LIMIT),)
  
  if len(sys.argv) == 4:
    PI = plan_parser.parse_plan(open(sys.argv[3]).read())
  else:
    PI = optic.do_optic(M[1].initial_state, time_limit=PLANNING_TIME_LIMIT)

  bitsA = ["observe", "_", "_"]
  bitsB = ["survey", "_", "_", "_", "_"]
  A = planning_types.PlanAction(-1, bitsA[0], bitsA[1:], -1)
  B = planning_types.PlanAction(-1, bitsB[0], bitsB[1:], -1)
  print (A, B)
  print (why_b_then_a(PI, A, B, optic, M, depth=1, make_comparison=True))


