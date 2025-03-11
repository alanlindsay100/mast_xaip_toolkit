
import sys

from ..planning import planner, simulator
from ..pddl_resources import original_model_loader as model_loader, planning_types
from ..xaip_util import *



class DN_Extension(plan_comparison):  
  def __init__(self, spec, f, fn, tstr, PI):
    super(DN_Extension, self).__init__(PI, None, None)
    self.o1, self.o2 = spec
    self.f = f
    self.dot_fn = fn
    self.tstr=tstr
    self.V = None
    self.PIP = -1
  def __str__(self):
    v_str = ""
    if not self.V == None:
      v_str = "\nIn the current plan the function has values:\n  " + "\n  ".join(map(lambda v: "["+str(v[1])+"] " + str(v[0]),self.V))
    if self.dot_fn == None:
      return "A function already exists to monitor " + self.tstr + " with name: " + str(self.f) + v_str
    return "Added function: " + str(self.f) + " to monitor " + self.tstr + v_str

class DT_Extension(plan_comparison):  
  def __init__(self, spec, f, new, tstr, PI):
    super(DT_Extension, self).__init__(PI, None, None)
    self.o1 = spec
    self.f = f
    self.is_new = new
    self.tstr=tstr
    self.V = None
    self.PIP = -1
  def __str__(self):
    v_str = ""
    if not self.V == None:
      v_str = "\nIn the current plan the function has values:\n  " + "\n  ".join(map(lambda v: "["+str(v[1])+"] " + str(v[0]),self.V))
    if not self.is_new:
      return "A function already exists to monitor " + self.tstr + " with name: " + str(self.f) + v_str
    return "Added function: " + str(self.f) + " to monitor " + self.tstr + v_str

def add_duration_near_function(obj1, obj2, M, depth, MAST):
  return MAST.duration_near(obj1, obj2, M, depth)

def get_t_dn_str(obj1, obj2, MAST):
  o1_plural = MAST.is_compound_name(obj1)
  t = get_query_templates()[{False:0, True:1}[o1_plural]][8:-1]
  return t.replace("#O1", obj1).replace("#O2", obj2)

def monitor_duration_near(obj1, obj2, M, PI, MAST, depth):
  M_TAG = get_M_Tag(depth)
  (f_name, fn_name) = add_duration_near_function(obj1, obj2, M, depth, MAST)
  
  write_out_model(M, M_TAG)
  write_out_plan(PI, M_TAG)
  
  return DN_Extension((obj1, obj2), f_name[0], fn_name, get_t_dn_str(obj1, obj2, MAST), PI)

def propose_queries_to_use_duration_near(obj1, obj2, templates, MAST):
  f_str = get_t_dn_str(obj1, obj2, MAST)
  l=[]
  for t in templates:
    l.append(t.replace("#F", f_str))
  return l

def add_distance_travelled_function(obj1, M, depth, MAST):
  return MAST.distance_travelled(obj1, M, depth)

def get_t_dt_str(obj1):
  t = get_query_templates()[2][8:-1]
  return t.replace("#O1", obj1)

def monitor_distance_travelled(obj1, M, PI, MAST, depth):
  M_TAG = get_M_Tag(depth)
  (f_name, new) = add_distance_travelled_function(obj1, M, depth, MAST)
  
  write_out_model(M, M_TAG)
  write_out_plan(PI, M_TAG)
  
  return DT_Extension(obj1, f_name[0], new, get_t_dt_str(obj1), PI)
  
def propose_queries_to_use_distance_travelled(obj1, templates, MAST):
  f_str = get_t_dt_str(obj1)
  l=[]
  for t in templates:
    l.append(t.replace("#F", f_str))
  return l

def get_query_templates():
  return ["Monitor the duration that #O1 is near #O2.", "Monitor the duration that #O1 are near #O2.", "Monitor the total distance travelled by #O1."]



