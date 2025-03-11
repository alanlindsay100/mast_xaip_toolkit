
import re, sys, os

from ..planning import planner, pddl_io
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..util import command_runner as CR


script_dir = os.path.dirname(os.path.abspath(__file__))

VERBOSE=True


def check_rules_match(s_lst, rules):
  rel_rs = [r for r in (map(lambda x: x.split(" "), rules)) if r[0] in s_lst]
  for rule in rel_rs:
    rule = tuple(rule)
    rule_len = len(rule)
    for i in range(len(s_lst) - rule_len + 1):
      if tuple(s_lst[i:i + rule_len]) == rule:
        return True
  return False

def op_match(op_t, bits):
  b = check_rules_match(bits, tuple(op_t.verbs))
  if VERBOSE:
    if b: 
      print ("Matched operator", op_t.op.name, "in", bits)
    else:
      print ("No Match of operator", op_t.op.name, "in", bits)
  return b


def get_pos_objs(p_t, bits):
  possibles = list()
  for i in range(len(bits)):
    if bits[i] in p_t.objs:
      possibles.append(bits[i])
  return possibles

def p_match(p_t, bits):
  o_m = dict(); supported_is = list()
  for i in range(len(bits)):
    if bits[i] in p_t.objs:
      if VERBOSE:
        print ("Matched object", bits[i], )
      o_m[i] = [bits[i]]
      if p_match_preps(p_t, bits[:i]):
        if VERBOSE:
          print ("And prep in", bits[:i+1])
        supported_is.append(i)
      else:
        if VERBOSE:
          print ("in", bits)
  if len(supported_is) > 0:
    return True, [x for i in supported_is for x in o_m[i]]
  return False, [x for i in o_m.keys() for x in o_m[i]]

def p_match_preps(p_t, l):
  for prep in p_t.preps:
    if l[-len(prep):]==prep:
      return True
  return False

def force_in_leftovers(a_t, s, mask, matches):
  used = set(filter(lambda x: not x=="_", mask))
  num_forced=0
  m1={};m2={}
  for i, p_m in enumerate(a_t.param_sym_m):
    m2[i]=[]
    if matches[i+1]: continue
    pos = get_pos_objs(p_m, s)
    if len(pos) > 1: continue
    if len(pos) > 0:
      pos = pos[0]
      if pos in used : continue
      if not pos in m1:
        m1[pos] = []
      m1[pos].append(i)
      m2[i].append(pos)
  for k in m1:
    if len(m1[k])==1:
      i = m1[k][0]
      if len(m2[i]) == 1:
        if VERBOSE:
          print ("Forcing parameter " + str(i) + " to: " + str(k))
        mask[i+1]=k
        num_forced+=1
  return num_forced
    
def a_match(a_t, s):
  op_match_b = op_match(a_t.op_sym_m, s)
  matches = [op_match_b]
  mask = [a_t.op_sym_m.op.name]
  for p_m in a_t.param_sym_m:
    p_m_match, pmatches = p_match(p_m, s)
    matches.append(p_m_match)
    if p_m_match:
      if len(pmatches) > 1:
        print ("WARNING: strange matching in nl2action.py", pmatches)
      mask.append(pmatches[0])
    else:
      mask.append("_")
  v = len(list(filter(lambda x: x, matches)))
  v += 0.5 * force_in_leftovers(a_t, s, mask, matches)
  return v, mask



def _match_action(s, op_templates, threshold = 0):
  if len(op_templates) == 0: return
  groups = []
  s = list(map(lambda e: e.strip().lower(), s))
  for at in op_templates:
    groups.append(a_match(at, s))
  msup = max(list(map(lambda e: e[0], groups)))
  if VERBOSE:
    print ("GROUPS:" , groups, "Max value:",str(msup))
  if msup < threshold: return None
  msupA = [A for (v,A) in groups if v == msup]
  if VERBOSE:
    print ("Matched to: ", str(msupA))
  return msupA


def match_action(s, op_templates):
  if VERBOSE:
    print ("MATCHING: " + str(s))
  return _match_action(s, op_templates)

def match_function(s, op_templates):
  if VERBOSE:
    print ("MATCHING FUNCTION: " + str(s))
  #op_templates = parse_action_templates(script_dir + "/_function_templates_"+str(depth)+".yaml", match_function_name(M), M)
  return _match_action(s, op_templates, 0.6)

def match_object(s, os):
  if VERBOSE:
    print ("ATTEMPTING TO MATCH AN OBJECT WITH: " + str(s))
  if s.__class__ == str:
    s = s.split(" ")
  s = list(map(lambda e: e.strip().lower(), s))
  if VERBOSE:
    print ("OBJECT SET:", str(os))
  matches = []
  for e in s:
    if e.lower() in os:
      matches.append(e.lower())
  if VERBOSE:
    print ("Complete matches: ", matches)
  matches.sort(key=lambda x: len(x))
  if len(matches) > 0:
    match = matches[-1]
    print ("Object matching found:", match)
    return match
  print ("Object matching failed..")
  return None


