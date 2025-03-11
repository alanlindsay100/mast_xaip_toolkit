
from ..pddl_resources import planning_types


class tie_breaker:
  def __init__(self, f):
    self.f = f
    
class func:
  def __init__(self, f, tie_breaker=None):
    self.f = f
    self.tie_breaker = tie_breaker
  def __str__(self):
    s = ""
    if self.tie_breaker:
      s += " ; TIE BREAKER: " + str(self.tie_breaker)
    if isinstance (self.f, planning_types.CalcNodeFunc):
      p = self.f.func
      s = str(p.name + " " + " ".join(p.args)) + s
    else:
      s = str(self.f) + s
    return s
class tie_breaking_mult:
  pass
class num:
  pass

"""
(total-time )
(+ (* (total-time ) 0.001) (duration_near_auv2_survey1_loc2 ))
"""

class pddl_s:
  def __init__(self, s):
    self.s = s
    
  def __str__(self):
    return self.s
    
def default_description(m):
  return pddl_s(str(m))

def describe_metric(f):
  return "(" + str(_describe_metric(f)) + ")"

def _describe_metric(f):
  if isinstance(f, planning_types.CalcNodeBinaryFunc) :
    lhs = _describe_metric(f.lhs)
    rhs = _describe_metric(f.rhs)
    if f.rel == "*":
      print ("*", rhs, rhs.__class__)
      if isinstance(rhs, tie_breaking_mult):
        print ("TIE BREAKER MULTIPLIER on RHS")
        return tie_breaker(lhs)
    elif f.rel == "+":
      print ("+", lhs, lhs.__class__)
      if isinstance(lhs, tie_breaker):
        print ("TIE BREAKER on LHS")
        return func(rhs, lhs.f)
    print ("DEFAULT MADE!")
    return default_description(f)
  elif isinstance(f, planning_types.CalcNodeFunc) :
    return func(f)
  elif isinstance(f, planning_types.CalcNodeValue) :
    if f.value < 0.1:
      return tie_breaking_mult()
    return num()
  else:
    print("WARNING: metric descriptor has nothing for ", f, f.__class__)
  
