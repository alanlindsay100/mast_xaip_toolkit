from .. import xaip_tools
from . import nl2action


def create_function(pf):
  (q, p, f) = pf
  r = xaip_tools.plan_query(q, p)
  return f
  
def choose_best_function(fd, l):
  print ("-------", fd, "-------------------")
  for (q, p, f), descriptions in l:
    print (q, p, len(descriptions), "?")
    for d in descriptions:
      print ("      ", d)
      if d in fd:
        return (q, p, f) 

def get_potential_function(fd, interpretations):
  l = []
  fd = " ".join(fd)
  for interpretation in interpretations:
    l += interpretation.get_potential_functions(fd)
  pf = choose_best_function(fd, l)
  if pf:
    return create_function(pf) 

def get_function(fd, op_templates, interpretations):
  f = nl2action.match_function(fd, op_templates)
  if not f:
    f = [get_potential_function(fd, interpretations)]
  return f

