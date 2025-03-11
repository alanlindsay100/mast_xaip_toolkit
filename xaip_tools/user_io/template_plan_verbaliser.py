

def _time_str(t):
  #return "{:.3f}".format(t)
  return "{:.0f}".format(t)


class move_composition:
  def __init__(self, PI, params, op_templates):
    self.PI=PI
    self.mover_p, self.from_p, self.to_p = params
    self.ot = op_templates
  def render(self, td=True):
    end = ""
    if td:
      end = ", starting at " + _time_str(self.PI[0].time) + " and completing at " + _time_str(self.PI[-1].time + self.PI[-1].duration) + ""
    through = ", through " + " ".join(map(lambda x: x.arguments[self.to_p], self.PI[:-1]))
    #bits = self.ot.description.split(" ")
    #am = dict(zip(list(map(lambda p: p.param, self.ot.param_sym_m)), self.A.arguments))
    return "move " + self.PI[0].arguments[self.mover_p] + " from " + self.PI[0].arguments[self.from_p] + " to " + self.PI[-1].arguments[self.to_p] + through + end


class template_based_action:
  def __init__(self, A, ot):
    self.A=A
    self.ot=ot
  def render(self, td=True):
    end = ""
    if td:
      end = ", starting at " + _time_str(self.A.time) + " and completing at " + _time_str(self.A.time + self.A.duration) + ""
    bits = self.ot.description.split(" ")
    am = dict(zip(list(map(lambda p: p.param, self.ot.param_sym_m)), self.A.arguments))
    rebits = []
    for bit in bits:
      if bit in am:
        bit = am[bit]
      rebits.append(bit)
    return " ".join(rebits)+ end

class control_action:
  def __init__(self, A):
    self.A=A
  def render(self, td=True):
    end = ""
    if td:
      end = ", starting at " + _time_str(self.A.time) + " and completing at " + _time_str(self.A.time + self.A.duration)
    return "(Control action " + str(self.A.predicate) + end + ")"

class template_based_function:
  def __init__(self, f, ot):
    self.f=f
    self.ot=ot
  def render(self):
    bits = self.ot.description.split(" ")
    am = dict(zip(list(map(lambda p: p.param, self.ot.param_sym_m)), self.f.args))
    rebits = []
    for bit in bits:
      if bit in am:
        bit = am[bit]
      rebits.append(bit)
    return " ".join(rebits)

def make_entry(PI, moving_actions, op_templates):
  if len(PI) == 1:
    return make_action_entry(PI[0], op_templates)
  moving_action = get_relevant_move_action(PI[0], moving_actions)
  return move_composition(PI, (moving_action["mover_p"], moving_action["from_p"], moving_action["to_p"]), op_templates)

def make_function_entry(f, f_templates):
  sym = f.name
  for ot in f_templates:
    if ot.op_sym_m.op.name == sym:
      return template_based_function(f, ot)
  print ("WARNING: Plan verbaliser can't process input ", f)

def verbalise_function(f, f_templates):
  o = make_function_entry(f, f_templates)
  if not o == None:
    return o.render()
  return ""

def make_action_entry(A, op_templates):
  sym = A.predicate
  for ot in op_templates:
    if ot.op_sym_m.op.name == sym:
      return template_based_action(A, ot)
  return globals()["control_action"](A)

def get_action_str(A, op_templates):
  o = make_action_entry(A, op_templates)
  if not o == None:
    return o.render()
  return ""

"""
XXX These functions make simplifying assumptions for move action composition, which have not been based on static analysis
"""
def compatible(a1, PI, moving_action):
  if len(PI) == 0:
    return True
  if not a1.predicate == moving_action["pddl_op"] : return False
  a0 = PI[-1]
  if a0.predicate == moving_action["pddl_op"] and a0.arguments[moving_action["mover_p"]] == a1.arguments[moving_action["mover_p"]]:
    return True
  return False

def is_relevant(obj, A):
  return len (A.arguments) > 0 and obj in A.arguments

def get_relevant_move_action(a, moving_actions):
  for ma in moving_actions:
    if a.predicate == ma["pddl_op"]:
      return ma

def make_forward_chain(PI, i, included, moving_actions):
  included[i]=True
  chain = [PI[i]]
  ma = get_relevant_move_action(PI[i], moving_actions)
  if not ma:
    return chain
  obj = PI[i].arguments[ma["mover_p"]]
  for j in range(i+1, len(PI)):
    if is_relevant(obj, PI[j]):
      if compatible(PI[j], chain, ma):
        chain.append(PI[j])
        included[j]=True
      else:  
        break
  return chain
      

def process_plan(PI, SI, op_templates):
  nPI = list()
  i=0
  included = [False] * len(PI)
  moving_actions = list(map(lambda x: x["moving_action"], SI))
  while i < len(PI):
    if included[i]==False:
      nPI.append(make_entry(make_forward_chain(PI, i, included, moving_actions), moving_actions, op_templates))
    i+=1
  return nPI


def verbalise(PI, DOMAIN_INTERPRETATION, op_templates, td=True):
  return list(map(lambda a: a.render(td=td), process_plan(PI, DOMAIN_INTERPRETATION.spatial, op_templates)))
  



