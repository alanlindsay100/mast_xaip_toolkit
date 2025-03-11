
from ..pddl_resources.parder import PddlDomainParser, PddlProblemParser, PDDLPlanParser
from ..pddl_resources.planning_types import Problem, State
from ..util import FileUtil

print ("Warning: state_reclaimer.py parses only a single walk")


problem_parser = PddlProblemParser()
problem = None

def read_problem(problem_name) :
  global problem
  problem_lines = list(map(lambda x: x.decode("utf-8-sig").encode("utf-8").replace("\t","  "), FileUtil.readlines(problem_name,";")))
  problem = problem_parser.parse(problem_lines)
def parse_state(facts_lines) :
    tups = problem_parser.parder.read_all(list(filter(lambda l: not "total-cost" in l, facts_lines)))
    i = 0
    re_tups = []
    while i < len(tups) :
      if tups[i] == "[rf0]" :
        re_tups.append(["=", tups[i+1][0].split("_"), tups[i+3]])
        i+=4
      else :
        re_tups.append(tups[i])
        i+=1
    factGatherer = Problem()
    problem_parser.parse_initial_state(re_tups, factGatherer)
    factGatherer.initial_state.props = list(filter(lambda x: not x.name[:4] == "not-", factGatherer.initial_state.props))
    return factGatherer.initial_state
def read_relevant_facts(facts_path) :
  facts_lines = list(map(lambda x: x.decode("utf-8-sig").encode("utf-8").replace("\t","  "), FileUtil.readlines(facts_path,";")))
  return parse_state(facts_lines)
def breakIntoSubLists(l, breaker_el) :
  nl = []
  cl = []
  for e in l +[breaker_el] :
    if e == breaker_el :
      if len(cl) > 0 :
        nl.append(cl)
        cl = []
    else :
      cl.append(e)
  return nl
def breakIntoPlans(lines) :
  return breakIntoSubLists(lines, "@E")
def breakIntoStates(lines) :
  return breakIntoSubLists(lines, "@I")
def parse_state_list(state_lines) :
  plan_sls = breakIntoPlans(state_lines)[0] # ignore additional walks for now
  steps_inits = breakIntoStates(plan_sls)
  states = []
  for stepInit in steps_inits :
    states.append(parse_state(stepInit))
  return states
def getFullStates(staticPart, state) :
  ns = State()
  ns.props = staticPart.props + state.props
  ns.funcs = dict(staticPart.funcs.items() + state.funcs.items())
  return ns
def getIrrelevantFacts(relevant_facts, backgroundState) :
  props = filter(lambda p: not p in relevant_facts.props, backgroundState.props)
  funcs = dict(filter(lambda f: not f[0] in relevant_facts.funcs.keys(), backgroundState.funcs.items()))
  ns = State()
  ns.props = props; ns.funcs = funcs
  return ns



def read_state_lines(base_state, states_path, relevant_facts_path) :
  relevant_facts = read_relevant_facts(relevant_facts_path)
  irrelevantFacts = getIrrelevantFacts(relevant_facts, base_state)
  state_lines = FileUtil.readlines(states_path,";")
  states = parse_state_list(state_lines)
  full_states = list(map(lambda ps: getFullStates(irrelevantFacts, ps), states))
  return full_states




