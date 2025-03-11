
import os

from .planning_helper import run_optic, get_optic_instantiations, run_tamer, run_optic_client, get_optic_instantiations_client
from .pddl_io import read_domain, read_problem, read_plan, write_out_problem, write_out_plan

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)

class planner:
  def __init__(self, domain_path, domain, base_problem, g, metric) :
    self.domain_path = domain_path
    self.domain = domain
    self.base_problem = base_problem
    self.goal = g
    self.metric=metric
    
  def is_goal_state(self, s):
    return self.goal.supported(s)
    
  def do_optic(self, s, time_limit=1800, memory_limit=8000000, code_ret=False, client=False):
    problem_filename = parent_directory +"/_temp_problem_for_optic.pddl"
    write_out_problem(problem_filename, self.base_problem, s, self.goal, self.metric)
    if client:
      return run_optic_client(self.domain_path, problem_filename, time_limit=time_limit, memory_limit=memory_limit, code_ret=code_ret)
    else:
      return run_optic(self.domain_path, problem_filename, time_limit=time_limit, memory_limit=memory_limit, code_ret=code_ret)
      
  def get_optic_actions(self, s, time_limit=1800, memory_limit=8000000,client=False):
    problem_filename = parent_directory+"/_temp_problem_for_optic.pddl"
    write_out_problem(problem_filename, self.base_problem, s, self.goal, self.metric)
    if not client:
      return get_optic_instantiations(self.domain_path, problem_filename, time_limit=time_limit, memory_limit=memory_limit)
    else:
      return get_optic_instantiations_client(self.domain_path, problem_filename, time_limit=time_limit, memory_limit=memory_limit)
  def do_tamer(self, s):
    problem_filename = parent_directory+"/_temp_problem_for_optic.pddl"
    write_out_problem(problem_filename, self.base_problem, s, self.goal, self.metric)
    return run_tamer(self.domain_path, problem_filename)


def get_the_planner(domain_path, problem_path, metric=False) :
  domain = read_domain(domain_path) # necessary?
  original_problem = read_problem(problem_path)
  goal = original_problem.goal

  return planner(domain_path, domain, original_problem, goal, metric)

def generate_plan(the_planner, state) :
  return the_planner.plan(state)[0]

def apply(the_planner, state, pi) :
  return the_planner.simulate_plan(state, pi)[1][-1]
