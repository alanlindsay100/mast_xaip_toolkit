

from ..pddl_resources.parder import PddlDomainParser, PddlProblemParser, PDDLPlanParser
from ..pddl_resources.planning_types import ConjGoal, PropGoal, InstDiscreteAction, NegPropGoal
from ..util import FileUtil



LOG=False

domain_parser = PddlDomainParser()
problem_parser = PddlProblemParser()
plan_parser = PDDLPlanParser()


def read_domain(domain_name) :
  if LOG:
    print ("Reading in domain: " + domain_name)
  domain_lines = list(map(lambda x: x.decode("utf-8-sig").encode("utf-8").replace("\t","  "), FileUtil.readlines(domain_name, ";")))
  return domain_parser.parse(domain_lines)

def read_problem(problem_name) :
  problem_lines = list(map(lambda x: x.decode("utf-8-sig").encode("utf-8").replace("\t","  "), FileUtil.readlines(problem_name,";")))
  return problem_parser.parse(problem_lines)

def read_plan(plan_name) :
  plan_lines = list(map(lambda x: x.decode("utf-8-sig").encode("utf-8").replace("\t","  "), FileUtil.readlines(plan_name, ";")))
  return plan_parser.parse(plan_lines, domain)


# think I'd need a problem too
def write_out_problem(problem_path, supporting_problem, s, g, METRIC=True, HIDDEN=False) :
  TAB = "  "
  headerStr = "(define (problem " + supporting_problem.name + ")\n"
  headerStr += TAB + "(:domain " + supporting_problem.domain + ")\n"
  headerStr += TAB + "(:objects \n"
  # objects
  for otype in set(map(lambda e: e[1], supporting_problem.objects.items())):
    headerStr+= 2*TAB + " ".join(map(lambda e: e[0], filter(lambda e: e[1]==otype, supporting_problem.objects.items()))) + " - " + otype + "\n"
  #headerStr += "".join(map(lambda (o,t): TAB+TAB + o + " - " + t + "\n", baseline_problem.objects.items()))
  headerStr += TAB + ")\n"
  headerStr += TAB + "(:init\n"
  # stationary state
  headerStr += "".join(map(lambda x: 2*TAB + str(x.pddl_str()) + "\n", s.props))
  headerStr += "".join(map(lambda e: 2*TAB +"(= " + str(e[0].pddl_str()) + " " + str(e[1]) + ")\n",  s.funcs.items()))
  if not s.tils == None: 
    for til in s.tils:
      headerStr += 2 * TAB + str(til) + "\n"
  if METRIC and not supporting_problem.metric:
    if len(filter(lambda p: p.name=="total-cost", s.funcs.keys()))==0:
      headerStr += 2*TAB + "(= (total-cost) 0)\n"
  headerStr += TAB + ")\n"
  if HIDDEN:
    headerStr += TAB + "(:hidden )\n"
  goalStr = TAB + "(:goal\n" + TAB + str(g) + "\n" +TAB + ")"
  if METRIC:
    if supporting_problem.metric:
      metricStr = str(supporting_problem.metric)
    else:
      metricStr = "(:metric minimize (total-cost))"
  ### Problem str ###

  modelStr = headerStr
  #modelStr += TAB+")\n" #??
  modelStr += goalStr + "\n"
  if METRIC :
    modelStr += TAB + metricStr + "\n"
  FileUtil.write(problem_path, modelStr+")")


def write_out_domain(domain_path, domain) :
  domain_str = str(domain)
  FileUtil.write(domain_path, domain_str)


def write_out_plan(plan_path, plan) :
  plan_str = "\n".join(map(lambda x: " ".join(x), plan))
  FileUtil.write(plan_path, plan_str)

def parse_plan(lines) :
  return list(map(lambda l: l.split(" "), filter(lambda x: not "." in x, filter(lambda l: not l == "", map(lambda l: l.strip(), lines)))))

def parse_raw_plan(lines, metric=False) :
  return resultExtractor(lines)

"""
ff: parsing domain file
domain 'grid' defined
 ... done.
ff: parsing problem file
problem 'grid-1' defined
 ... done.
translating negated cond for predicate open-move
translating negated cond for predicate nok
translating negated cond for predicate confused
translating negated cond for predicate =
translating negated cond for predicate moved
task contains conditional effects. turning off state domination.
ff: search configuration is A*epsilon with weight 5.
Metric is ((1.00*[RF0](total-cost)) - () + 0.00)
COST MINIMIZATION DONE (WITH cost-minimizing relaxed plans).
Advancing to goal distance:    7
                               6
                               5
                               4
                               3
                               2
                               1
                               0
ff: found legal plan as follows
step    0: explain-default r1 b2
        1: indicatemove r1 b2 b3
        2: enactmove r1 b2 b3
        3: interpret-move r1 b2 b3 b3
        4: tidyup r1 b2 b3 b3
        5: indicatemove r1 b3 c3
        6: enactmove r1 b3 c3
        7: interpret-move r1 b3 c3 c3
        8: tidyup r1 b3 c3 c3
        9: pickup r1 c3 key1
       10: indicatemove r1 c3 b3
       11: enactmove r1 c3 b3
       12: interpret-move r1 c3 b3 b3
       13: tidyup r1 c3 b3 b3
       14: indicatemove r1 b3 c3
       15: enactmove r1 b3 b2
       16: interpret-move r1 b3 b2 c3
       17: explain-confused-mistake r1 b3 b2 c3
       18: tidyup r1 b3 b2 c3
       19: unlock r1 b2 b1 key1 shape1
       20: putdown r1 b2 key1
       21: indicatemove r1 b2 b1
       22: enactmove r1 b2 b1
       23: interpret-move r1 b2 b1 b1
       24: tidyup r1 b3 b1 c3
       25: explain-default r1 b1
       26: indicatemove r1 b1 c1
       27: enactmove r1 b1 c1
       28: interpret-move r1 b1 c1 c1
       29: tidyup r1 b2 c1 b1
plan cost: 49.000000
time spent:    0.00 seconds instantiating 1001 easy, 0 hard action templates
               0.00 seconds reachability analysis, yielding 144 facts and 488 actions
               0.00 seconds creating final representation with 138 relevant facts, 1 relevant fluents
               0.01 seconds computing LNF
               0.00 seconds building connectivity graph
               7.64 seconds searching, evaluating 43895 states, to a max depth of 0
               7.65 seconds total time
"""

def metricResultExtractor(lines) :
  plan = []
  suckUpPlan = success = False
  n = -1; c = -1
  for line in lines :
    if "ff: goal can be simplified to TRUE. The empty plan solves it" in line :
      return [], True
    elif "ff: goal can be simplified to FALSE. No plan will solve it" in line:
      return None, False
    if suckUpPlan :
      if "time spent:" in line or line == '\n' or line == "" or "plan cost:" in line :
        suckUpPlan = False
      else :
        if ":" in line :
          cols = line.split(":")
          plan.append(cols[1].strip().split(" "))
          print ("CHEWING:", cols[1].strip().split(" "))
    if "ff: found legal plan as follows" in line :
      print ("NOTICED: SUCCESS")
      success = True
      suckUpPlan = True
    if "seconds total time" in line :
      t = float(line[:-20])
  if not success :
    plan = None
  return plan, success

def resultExtractor(lines) :
  plan = []
  suckUpPlan = success = False
  n = -1; c = -1
  for line in lines :
    if "ff: goal can be simplified to TRUE. The empty plan solves it" in line :
      return [], True
    elif "ff: goal can be simplified to FALSE. No plan will solve it" in line:
      return None, False
    if suckUpPlan :
      if "time spent:" in line or line == '\n' or line == "" or "plan cost:" in line :
        suckUpPlan = False
      else :
        if ":" in line :
          cols = line.split(":")
          plan.append(cols[1].strip().split(" "))
    if "ff: found legal plan as follows" in line :
      success = True
      suckUpPlan = True
    if "seconds total time" in line :
      t = float(line[:-20])
  if not success :
    plan = None
  return plan, success


# written out for goal recognition software
def write_out_goal(goal_path, goal) :
  if isinstance(goal, ConjGoal) :
    goal_str = ",".join(map(lambda g: str(g), goal.conj))
  elif isinstance(goal, list) :
    goal_str = ",".join(map(lambda g: str(g), goal))
  else :
    print ("Not implemented: pddl_io goal writer currently expects a conjunction..")
    goal_str = ""
  FileUtil.write(goal_path, goal_str)
