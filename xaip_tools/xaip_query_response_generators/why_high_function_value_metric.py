
import sys

from ..planning import pddl_io, simulator
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *
from . import constraint_support
from ..abstraction import abstraction_fe as abstraction


class FV_comparison(plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(FV_comparison, self).__init__(PI, M, metrics)
    self.f = spec

  def get_query(self):
    return "f (" + " ".join(self.f) + ") so high"
  def get_dont_do_it(self):
    return "reduce this function"


def get_functions(M):
  return list(map(lambda x: [x.name] + x.args , M[1].initial_state.funcs.keys()))

def insist_on_low_fv(f, M):
  M[1].metric.f = f

def make_optimisation_function(f, n, M, M_TAG):
  F = filter(lambda x: arg_match(x, f), get_functions(M))
  F = list(map(lambda f: planning_types.CalcNodeFunc(planning_types.Proposition(f[0],f[1:])), F))
  s = F[0]
  for b in F[1:]:
    s = planning_types.CalcNodeBinaryFunc("+", b, s)
  #return planning_types.CalcNodeBinaryFunc("+", M[1].metric.f, s)
  inv_n = 1.0-n
  return planning_types.CalcNodeBinaryFunc("+", planning_types.CalcNodeBinaryFunc("*", M[1].metric.f, planning_types.CalcNodeValue(inv_n)), planning_types.CalcNodeBinaryFunc("*", s, planning_types.CalcNodeValue(n)))

def why_high_fv(optic1, M, PI, f, n, metrics, DOMAIN_INTERPRETATION, depth):
  M_TAG = get_M_Tag(depth)
  of = make_optimisation_function(f, n, M, M_TAG)
  metrics.append(of)
  comparison = FV_comparison(f, PI, M, metrics)
  insist_on_low_fv(of, M)
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison
  
def get_query_templates():
  return ["Why not minimise #F?", "Why not minimise #F with a weight of #R?"]



