import sys


from . import parder as Parser
from . import planning_types as Types


def pddl_file_line_reader(fn):
  return list(map(lambda x: x.split(";")[0], map(lambda x: x.strip(), open(fn).readlines())))

def make_new_predicate(psym, args=None):
  p=Types.ParameterList(psym)
  if args:
    p.add_parameter(args)
  return p

def read_domain (domain_fn):
  domain_lines = pddl_file_line_reader(domain_fn)
  domain_parser = Parser.PddlDomainParser()
  return domain_parser.parse(domain_lines)

def read_problem (problem_fn):
  problem_lines = pddl_file_line_reader(problem_fn)
  problem_parser = Parser.PddlProblemParser()
  return problem_parser.parse(problem_lines)

def get_planning_model(domain_fn,  problem_fn):
  domain = read_domain(domain_fn)
  problem = read_problem(problem_fn)
  return (domain, problem)


if __name__ == "__main__":
  domain, problem = get_planning_model(sys.argv[1], sys.argv[2])
  print (problem.objects)

  print (list(map(lambda x: x.name, domain.actions)))
