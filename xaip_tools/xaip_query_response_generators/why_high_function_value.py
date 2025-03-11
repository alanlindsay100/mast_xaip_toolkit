
import sys

from ..planning import pddl_io, simulator
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *
from . import constraint_support
from ..abstraction import abstraction_fe as abstraction


"""
* XXX Part of this is only applicable if each action only updates any specific function with the same parameter sets. E.g., transferring pcus between links would break it.
* It is also done sillily because the action splitting uses all the arguments..
"""
USE_FINISH_ACTION=False

class FV_comparison(plan_comparison):  
  def __init__(self, spec, PI, M, metrics):
    super(FV_comparison, self).__init__(PI, M, metrics)
    self.f = spec
  def get_query(self):
    return "f (" + " ".join(self.f) + ") so high"
  def get_dont_do_it(self):
    return "reduce this function"

def get_current_metric_value(M, PI, mask, t=sys.maxsize):
  s = simulator.get_current_metric_state(M, PI, t)
  F = filter(lambda x: arg_match([x.name] + x.args, mask), M[1].initial_state.funcs.keys())
  v = sum(map(lambda p: s.funcs[p], F))
  print ("Current function mask valuation:", v)
  return v
  
def make_splitting_pred(F, M, M_TAG, tag=""):
  df = filter(lambda f: f.name == F[0].name, M[0].functions)[0]
  pred_sym = F[0].name+"_constraint" +M_TAG +"_"+tag
  p = planning_types.ParameterList(pred_sym)
  p.add_parameter((df.parameters.type_list, df.parameters.param_list))
  M[0].predicates.append(p)
  return pred_sym

def extend_initial_state(pred_sym, args_set, M):
  new_preds = list(map(lambda args: planning_types.Proposition(pred_sym, args), args_set))
  M[1].initial_state.props += new_preds
  
def get_accumulation_predicate(mask, M, M_TAG):
  pred_sym = "f_accum_" + M_TAG
  f = planning_types.ParameterList(pred_sym)
  M[0].add_function(f)
  F = filter(lambda x: arg_match([x.name] + x.args, mask), M[1].initial_state.funcs.keys())
  v = sum(map(lambda p: M[1].initial_state.funcs[p], F))
  M[1].initial_state.funcs[planning_types.Proposition(pred_sym,[])]=v
  return pred_sym  

def get_f_effectors(f, M):
  rops = []
  for op in M[0].actions:
    fs = []
    for eff in op.at_start_e + op.at_end_e:
      if eff.__class__ == planning_types.FuncIncrease or eff.__class__ == planning_types.FuncDecrease or eff.__class__ == planning_types.FuncAssign:
        F = eff.lhs.func
        if f[0] == F.name:
          if not F in fs:
            fs.append(F)
    if len(fs)>0:
      rops.append((op, fs))
  return rops

def copy_for_accumulator(acc_psym, eff):
  return eff.__class__(planning_types.CalcNodeFunc(planning_types.Proposition(acc_psym, [])), eff.rhs)
  

def add_f_effect_to_accumulator(f, f_rops, acc_psym):
  for op in f_rops:
    for eff_t in (op.at_start_e, op.at_end_e):
      to_add = []
      for eff in eff_t:
        if eff.__class__ == planning_types.FuncIncrease or eff.__class__ == planning_types.FuncDecrease or eff.__class__ == planning_types.FuncAssign:
          F = eff.lhs.func
          if f[0] == F.name:
            to_add.append(copy_for_accumulator(acc_psym, eff))
      eff_t += to_add
          
def make_splitting_pred(op, M, M_TAG, tag=""):
  pred_sym = op.name+"_constraint" +M_TAG +"_"+tag
  p = planning_types.ParameterList(pred_sym)
  p.add_parameter((op.parameters.type_list, op.parameters.param_list))
  M[0].predicates.append(p)
  return pred_sym

def add_operators_condition(pred_sym, op):
  p = planning_types.Predicate(pred_sym)
  p.vars = op.parameters.param_list
  op.at_start_c.append(planning_types.PropGoal(p))

def extend_initial_state(pred_sym, args_set, M):
  new_preds = list(map(lambda args: planning_types.Proposition(pred_sym, args), args_set))
  M[1].initial_state.props += new_preds

def extract_args(arg_is, x):
  return list(map(lambda i: x[i], arg_is))

def split_op_by_action(ops, f, M, M_TAG):
  ops_f,ops_nf = list(), list()
  for (op, Fs) in ops:
    fop = op.clone()
    ops_f.append(fop); M[0].actions.append(fop)
    ops_nf.append(op)
    aps = make_splitting_pred(op, M, M_TAG, tag="a")
    naps = make_splitting_pred(op, M, M_TAG, tag="na")
    add_operators_condition(aps, fop)
    add_operators_condition(naps, op)
    
    print ("WARNING: we're only considering one F per operator in why_high_function_value..")
    F=Fs[0]
    arg_is = list(map(lambda arg: op.parameters.param_list.index(arg), F.vars))
    if len(F.vars) == 0:
      F_params = list(map(lambda x: (x.arguments, [f[0]]) , filter(lambda act: act.predicate == op.name, M[2])))
    else:
      F_params = list(map(lambda x: (x.arguments,[f[0]] + extract_args(arg_is, x.arguments)), filter(lambda act: act.predicate == op.name, M[2])))
    #print ("**", F_params, op.name)
    f_params = list(map(lambda x: x[0], filter(lambda x: arg_match(x[1], f), F_params)))
    extend_initial_state(aps, f_params, M)
    
    nf_params = list(map(lambda x: x[0], filter(lambda x: not arg_match(x[1], f), F_params)))
    extend_initial_state(naps, nf_params, M)
  return ops_f,ops_nf


def split_actions_and_accumulate_effects(acc_psym, f, M, M_TAG):
  rops = get_f_effectors(f, M)
  ops_f,ops_nf = split_op_by_action(rops, f, M, M_TAG)
  add_f_effect_to_accumulator(f, ops_f, acc_psym)
  

def add_constraint_to_finish_action(acc_psym, v, M):
  accf = planning_types.CalcNodeFunc(planning_types.Proposition(acc_psym, []))
  fop = list(filter(lambda x: x.name == "finish", M[0].actions))[0]
  fop.at_start_c.append(planning_types.CalcNodeBinaryRel("<", accf, v))

def add_constraint_to_goal(acc_psym, v, M):
  accf = planning_types.CalcNodeFunc(planning_types.Proposition(acc_psym, []))
  try:
    conj = M[1].goal.conj
  except:
    conj = [M[1].goal]
    M[1].goal = planning_types.ConjGoal(conj)
  conj.append(planning_types.CalcNodeBinaryRel("<", accf, v))

def insist_on_lower_fv(f, v, M, M_TAG):
  if len (f) > 1:
    acc_psym = get_accumulation_predicate(f, M, M_TAG)
    split_actions_and_accumulate_effects(acc_psym, f, M, M_TAG)
  else:
    acc_psym = f[0]
  if USE_FINISH_ACTION: # XXX note the model needs to provide the finish function
    add_constraint_to_finish_action(acc_psym, v, M)
  else:
    add_constraint_to_goal(acc_psym, v, M)  

def why_high_fv(optic1, M, PI, f, metrics, DOMAIN_INTERPRETATION, depth, reduction_perc=0):
  M_TAG = get_M_Tag(depth)
  comparison = FV_comparison(f, PI, M, metrics)
  pi_f_v = get_current_metric_value(M, PI, f)

  if pi_f_v > 0:
    v = 100 - reduction_perc
  else:
    v = 100 + reduction_perc
  mp = v * 0.01
  pi_f_v=pi_f_v*mp

  insist_on_lower_fv(f, pi_f_v, M, M_TAG)
  write_out_model(M, M_TAG)
  PIP = abstraction.make_abs_plan(depth, DOMAIN_INTERPRETATION)
  
  comparison.record_final_plan(PIP, M)
  return comparison

  
def get_query_templates():
  return ["Why is #F high?"]




