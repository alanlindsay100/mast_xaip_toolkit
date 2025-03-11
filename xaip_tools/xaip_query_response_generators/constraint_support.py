
from enum import Enum
from ..pddl_resources import planning_types
from ..xaip_util import arg_match



def make_splitting_pred(pmask, op, M, M_TAG, tag=""):
  pred_sym = "op_splitter_"+tag + "_" + op.name+"_" +M_TAG
  p = planning_types.ParameterList(pred_sym)
  p.add_parameter((get_els(op.parameters.type_list, pmask), get_els( op.parameters.param_list, pmask)))
  M[0].predicates.append(p)
  return pred_sym

def add_operators_condition(pmask, pred_sym, ops):
  p = planning_types.Predicate(pred_sym)
  p.vars = get_els(ops[0].parameters.param_list, pmask) #list(map(lambda i: ops[0].parameters.param_list[i], pmask))
  list(map(lambda op: op.at_start_c.append(planning_types.PropGoal(p)), ops))

def extend_initial_state(pred_sym, args_set, M):
  new_preds = list(map(lambda args: planning_types.Proposition(pred_sym, args), args_set))
  M[1].initial_state.props += new_preds

# XXX the intention here would be to organise these by parameter set (to reduce making preds..)
# There shouldn't be any procedure that changes the parameters, so we're checking and returning
# a single set.
def organise_ops(ops):
  #return map(lambda op: [op], ops)
  pz = ops[0].parameters
  for op in ops:
    assert pz == op.parameters
  return [ops]

def get_els(els, iz):
  return tuple(map(lambda i: els[i], iz))

def split_op_by_action(ops, A, M, M_TAG):
  for op in ops:
    M[0].actions.remove(op)
  op_groups = organise_ops(ops)
  ops_A,ops_nA = list(), list()
  pmask = list(filter(lambda i: not A.arguments[i]=="_", range(len(A.arguments))))
  for op_g in op_groups:
    A_ops = list(map(lambda a: a.clone(), op_g))
    nA_ops = list(map(lambda a: a.clone(), op_g))
    
    aps = make_splitting_pred(pmask, ops[0], M, M_TAG, tag="a")
    naps = make_splitting_pred(pmask, ops[0], M, M_TAG, tag="na")
    add_operators_condition(pmask, aps, A_ops)
    add_operators_condition(pmask, naps, nA_ops)
    A_actions = list(filter(lambda act: act.predicate == A.predicate and arg_match(act.arguments, A.arguments), M[2]))
    l = set()
    for a in A_actions:
      l.add(get_els(a.arguments, pmask))
    extend_initial_state(aps, l, M)
    nA_actions = list(filter(lambda act: act.predicate == A.predicate and not arg_match(act.arguments, A.arguments), M[2]))
    l = set()
    for a in nA_actions:
      l.add(get_els(a.arguments, pmask))
    extend_initial_state(naps, l, M)
    ops_A += A_ops; ops_nA += nA_ops
  M[0].actions += ops_A + ops_nA
  return ops_A,ops_nA

def add_effect(ops, Psym):
  p = planning_types.Predicate(Psym)
  list(map(lambda op: op.at_end_e.append(planning_types.PropAssign(p)), ops))

def add_precondition(ops, Psym):
  p = planning_types.Predicate(Psym)
  list(map(lambda op: op.at_start_c.append(planning_types.PropGoal(p)), ops))

def add_fact_to_goal(M, psym, args=[]):
  p = planning_types.PropGoal(planning_types.Proposition(psym, args))
  try:
    g=M[1].goal.conj
  except:
    g=[M[1].goal]
  g.append(p)
  M[1].goal = planning_types.ConjGoal(g)

def get_splitting_tag(i):
  c = chr(ord('a') + i)
  return str(c)
def all_ops(A,M): return list(filter(lambda op: A.predicate==op.name, M[0].actions))
def split_ops_for_masks(ops, mask_seq, M, M_TAG):
  m = {}
  for op in M[0].actions:
    m[op] = []
  for i, mask in enumerate(mask_seq, 1):
    ops = all_ops(mask,M)
    ops_A,ops_nA = split_op_by_action(ops, mask, M, M_TAG + "_" + get_splitting_tag(i))
    for nop in ops_A:
      m[nop] = m[op] + [i]
    for nop in ops_nA:
      m[nop] = m[op]
    for op in ops: del m[op]
  return m    
  
  
def get_progress_level_psym(i, M_TAG):
  c = chr(ord('a') + i)
  return "progress_marker_"+M_TAG+"_"+str(c)
def make_progress_marker_symbols(n, M, M_TAG):
  for i in range(n+1):
    psym = get_progress_level_psym(i, M_TAG)
    p = planning_types.ParameterList(psym)
    M[0].predicates.append(p)
  psym = get_progress_level_psym(0, M_TAG)
  M[1].initial_state.props.append(planning_types.Proposition(psym, []))
def add_prec_at_progress_level(a, i, M_TAG):
  psym = get_progress_level_psym(i, M_TAG)
  a.at_start_c.append(planning_types.PropGoal(planning_types.Predicate(psym)))
def del_progress_level(a, i, M_TAG):
  psym = get_progress_level_psym(i, M_TAG)
  a.at_end_e.append(planning_types.NegPropAssign(planning_types.Predicate(psym)))
def add_progress_level(a, i, M_TAG):
  psym = get_progress_level_psym(i, M_TAG)
  a.at_end_e.append(planning_types.PropAssign(planning_types.Predicate(psym)))
def make_progression_version(cpa, i, M_TAG):
  a = cpa.clone()
  add_prec_at_progress_level(a, i-1, M_TAG)
  del_progress_level(a, i-1, M_TAG)
  add_progress_level(a, i, M_TAG)
  return a
def organise_actions(m, n):
  AiL = {}
  for i in range(1, n+1): AiL[i] = list()
  for op, v in m.items():
    for i in v:
      AiL[i].append(op)
  return AiL
OP_MOD_CATEGORY = Enum('OP_MOD_CATEGORY', [('FIRST', 1), ('LAST', 2), ('TRANSITION', 3), ('LOOP', 4), ('NONE', 5)])
  
def add_seq_progress_markers(m, mask_seq, M, M_TAG):
  L=[]
  last_ref = {}
  for a in m.keys(): last_ref[a] = 0
  make_progress_marker_symbols(len(mask_seq), M, M_TAG)
  
  AiL = organise_actions(m, len(mask_seq))
  
  for i in range(1,len(mask_seq)+1):
    
    Ai = AiL[i]
    
    for a in Ai:
      pa = make_progression_version(a, i, M_TAG) 
      t = [OP_MOD_CATEGORY.TRANSITION]
      if i == 1: t.append(OP_MOD_CATEGORY.FIRST)
      if i == len(mask_seq): t.append(OP_MOD_CATEGORY.LAST)
      L.append((pa, t))
      last_ref[a] = i
  for a, tup in m.items():
    t = [OP_MOD_CATEGORY.LOOP]
    if last_ref[a] > 0:
      add_prec_at_progress_level(a, last_ref[a], M_TAG)
      if last_ref[a] == 1: t.append(OP_MOD_CATEGORY.FIRST)
      if last_ref[a] == len(mask_seq): t.append(OP_MOD_CATEGORY.LAST)
    else:
      t.append(OP_MOD_CATEGORY.NONE)
    L.append((a, t))
  M[0].actions = list(map(lambda e: e[0], L))
  final_sym = get_progress_level_psym(len(mask_seq), M_TAG)
  return L, final_sym

def identify_seq_in_ops(mask_seq, M, M_TAG):
  ops_m = split_ops_for_masks(M[0].actions, mask_seq, M, M_TAG)
  return add_seq_progress_markers(ops_m, mask_seq, M, M_TAG)

    
    


  

