
import sys, time
import pytamer
from pytamer import *
from fractions import Fraction


def get_time():
  return time.process_time()

def plan(dfn, pfn, opt="1"):
  start = get_time()
  tenv = tamer_env_new()
  problem = tamer_parse_pddl(tenv, dfn, pfn) 
  try:
    if opt == "1":
      tamer_env_set_vector_string_option(tenv, 'ftp-heuristic', ['hadd'])
      pi = tamer_do_ftp_planning(problem)
    elif opt == "2":
      pi = tamer_do_smt_planning(problem, 20)
    else:
      pi = tamer_do_iw_planning(f)
  except Exception as e:
    print (e)
    return None
  steps = tamer_ttplan_get_steps(pi)
  plan_time = get_time() - start

  st = ";; PLAN (planning time: " + str(plan_time) + "s):\n"
  for s in steps:
    a = tamer_ttplan_step_get_action(s)
    name = pytamer.tamer_action_get_name(a)
    x = Fraction(pytamer.tamer_ttplan_step_get_start_time(s))
    start = float(x)
    duration = int(Fraction(pytamer.tamer_ttplan_step_get_duration(s)))
    params = []
    for p in pytamer.tamer_ttplan_step_get_parameters(s):
      o = pytamer.tamer_expr_get_instance(tenv, p)
      params.append(str(o))
    st += str(start) +": (" + str(name)[len("action_"):] + " " + " ".join(params) +") ["+str(duration)+"]\n" 
  return st
  
if __name__ == '__main__':
  domain_path, problem_path = sys.argv[1:3]
  print (plan(domain_path, problem_path))
