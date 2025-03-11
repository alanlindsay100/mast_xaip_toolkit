




def instantiatePred(params, abp) :
  return Proposition(abp.name, list(map(lambda v: params[v], abp.vars)))


class Effect(object) :
  def funcUpdate(self, nextS, fkey, rhsV) :
    nextS.funcs[fkey] = rhsV

class ConjEffect(Effect) :
  def __init__(self, l) :
    self.conj = l

  def apply(self, currentS, nextS, paramMap) :
    for e in self.conj :
      e.apply(currentS, nextS, paramMap)

  def get_pos_effs(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_pos_effs(parmaMap), self.conj)))
  def get_neg_effs(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_neg_effs(parmaMap), self.conj)))


  def __str__(self) :
    return "(and\n    " + "\n    ".join(map(lambda x: ""+x.__str__(), self.conj)) + ")"

class ConditionalEffect(Effect):
  def __init__(self, lhs, rhs):
    self.lhs = lhs
    self.rhs = rhs
    
  def apply(self, currentS, nextS, paramMap) :
    if self.lhs.supported(currentS, parmaMap):
      self.rhs.apply(currentS, nextS, paramMap)
  
  def __str__(self):
    return "(when " + str(self.lhs) + " " + str(self.rhs) + ")"

class OneOfEffect(Effect):
  def __init__(self, lhs, rhs):
    self.lhs = lhs
    self.rhs = rhs
    
  def __str__(self):
    return "(oneof " + str(self.lhs) + " " + str(self.rhs) + ")"

class PropAssign(Effect) :
  def __init__(self, p) :
    self.prop = p

  def apply(self, currentS, nextS, paramMap) :
    prop = self.prop.instantiate(paramMap)
    if not prop in currentS.props:
      nextS.props.append(prop)

  def get_pos_effs(self, parmaMap=None) :
    return self.prop.instantiate(parmaMap)
  def get_neg_effs(self, parmaMap=None) :
    return None

  def __str__(self) :
    #return "("+str(self.prop)+")"
    return str(self.prop)

class NegPropAssign(PropAssign) :
  def __init__(self, p) :
    super(NegPropAssign, self).__init__(p)

  def __str__(self) :
    #return "(not ("+str(self.prop)+"))"
    return "(not "+str(self.prop)+")"

  def apply(self, currentS, nextS, parmaMap) :
    prop = self.prop.instantiate(parmaMap)
    if prop in currentS.props:
      nextS.props.remove(prop)

  def get_neg_effs(self, parmaMap=None) :
    return self.prop.instantiate(parmaMap)
  def get_pos_effs(self, parmaMap=None) :
    return None

"""class FuncPred(Effect) :
  def __init__(self, p) :
    self.prop = p

  def __str__(self) :
    return "("+str(self.prop)+")"
"""

class FuncAssign(Effect) :
  def __init__(self, lhs, rhs) :
    self.lhs = lhs
    self.rhs = rhs
  
  def apply(self, currentS, nextS, paramMap) :
    rhsV = self.rhs.evaluate(currentS, paramMap)
    self.funcUpdate(nextS, self.lhs.func.instantiate(paramMap), rhsV)

  def __str__(self) :
    return "(assign " + str(self.lhs) + " " + str(self.rhs) + ")"

class FuncIncrease(FuncAssign) :
  def __init__(self, lhs, rhs) :
    super(FuncIncrease,self).__init__(lhs,rhs)

  def apply(self, currentS, nextS, paramMap) :
    lhsV = self.lhs.evaluate(currentS, paramMap)
    rhsV = self.rhs.evaluate(currentS, paramMap)
    self.funcUpdate(nextS, self.lhs.func.instantiate(paramMap), lhsV + rhsV)

  def get_neg_effs(self, parmaMap=None) :
    return None
  def get_pos_effs(self, parmaMap=None) :
    return None

  def __str__(self) :
    return "(increase " + str(self.lhs) + " " + str(self.rhs) + ")"

class FuncDecrease(FuncAssign) :
  def __init__(self, lhs, rhs) :
    super(FuncDecrease,self).__init__(lhs,rhs)

  def apply(self, currentS, nextS, paramMap) :
    lhsV = self.lhs.evaluate(currentS, paramMap)
    rhsV = self.rhs.evaluate(currentS, paramMap)
    self.funcUpdate(nextS, self.lhs.func.instantiate(paramMap), lhsV - rhsV)

  def __str__(self) :
    return "(decrease " + str(self.lhs) + " " + str(self.rhs) + ")"

class TIL(object):
  def __init__(self, t, eff):
    self.t = t
    self.eff = eff

  def __str__(self):
    return "(at " + str(self.t) + " " + str(self.eff) + ")"

class Goal(object) :
  pass


class ConjGoal(Goal) :
  def __init__(self, l) :
    self.conj = l
    self._hash = None

  def supported(self, currentS, parmaMap=None) :
    for e in self.conj :
      if not e.supported(currentS, parmaMap):
        return False
    return True

  def get_pos_goals(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_pos_goals(parmaMap), self.conj)))
  def get_neg_goals(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_neg_goals(parmaMap), self.conj)))

  def __eq__(self, p) :
    if not isinstance(p, ConjGoal): return False
    if len(self.conj) == len(p.conj):
      for e in self.conj:
        if not e in p.conj:
          return False
      return True
    return False

  def __hash__(self) :
    if self._hash == None :
      v = 1
      for e in self.conj:
        v *= hash(e)
    return self._hash
  
  def __str__(self) :
    return "(and\n    " + "\n    ".join(map(lambda x: ""+x.__str__(), self.conj)) + ")"

class DisjunctGoal(Goal) :
  def __init__(self, l) :
    self.conj = l

  def supported(self, currentS, parmaMap=None) :
    for e in self.conj :
      if e.supported(currentS, parmaMap):
        return True
    return False

  def get_pos_goals(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_pos_goals(parmaMap), self.conj)))
  def get_neg_goals(self, parmaMap=None):
    return list(filter(lambda x: not x==None, map(lambda x: x.get_neg_goals(parmaMap), self.conj)))
  
  def __str__(self) :
    return "(or\n    " + "\n    ".join(map(lambda x: ""+x.__str__(), self.conj)) + ")"

class PropGoal(Goal) :
  def __init__(self, p) :
    self.prop = p
    self._hash = None

  def supported(self, currentS, parmaMap=None) :
    prop = self.prop.instantiate(parmaMap)
    return prop in currentS.props

  def get_pos_goals(self, parmaMap=None) :
    return self.prop.instantiate(parmaMap)
  def get_neg_goals(self, parmaMap=None) :
    return None
  
  def __eq__(self, p) :
    if not p.__class__ ==PropGoal: return False
    return self.prop == p.prop

  def __hash__(self) :
    if self._hash == None :
      self._hash = hash(self.prop)
    return self._hash  
  
  def __str__(self) :
    #return "("+str(self.prop)+")"
    return str(self.prop)

class NegPropGoal(PropGoal) :
  def __init__(self, p) :
    super().__init__(p)

  def supported(self, currentS, parmaMap=None) :
    return not super(NegPropGoal,self).supported(currentS, parmaMap)

  def get_pos_goals(self, parmaMap=None) :
    return None
  def get_neg_goals(self, parmaMap=None) :
    return self.prop.instantiate(parmaMap)
  
  def __eq__(self, p) :
    if not isinstance(p, NegPropGoal): return False
    return self.prop == p.prop

  def __hash__(self) :
    if self._hash == None :
      self._hash = -hash(self.prop)
    return self._hash  
  
  def __str__(self) :
    #return "(not (" + str(self.prop)+"))"
    return "(not " + str(self.prop)+")"

class CalcNodeBinaryRel(Goal) :
  _evalFs = {">": (lambda e: e[0] > e[1]),
            "=": (lambda e: e[0] == e[1]),
            "<": (lambda e: e[0] < e[1]),
            "<=": (lambda e: e[0] <= e[1]),
            ">=": (lambda e: e[0] >= e[1]),
            "!=": (lambda e: not e[0] == e[1])
           }

  def __init__(self, rel, lhs, rhs) :
    self.rel = rel
    self.lhs = lhs
    self.rhs = rhs
    self._hash = None

  def evaluate(self, currentS, parmaMap) :
    lhsV = self.lhs.evaluate(currentS, parmaMap)
    rhsV = self.rhs.evaluate(currentS, parmaMap)
    return self._evalFs[self.rel]((lhsV,rhsV))

  def supported(self, currentS, parmaMap=None) :
    return self.evaluate(currentS, parmaMap)

  def __eq__(self, p) :
    if not isinstance(p, CalcNodeBinaryRel): return False
    return self.rel == p.rel and self.lhs == p.lhs and self.rhs == p.rhs

  def __hash__(self) :
    if self._hash == None :
      h = 17
      h = h * 31 + hash(self.rel)
      h = h * 31 + hash(self.lhs)
      h = h * 31 + hash(self.rhs)
      self._hash = h
    return self._hash  

  def __str__(self) :
    return "(" +self.rel + " " + str(self.lhs) + " " + str(self.rhs) + ")"

class CalcNode(object) :
  def __init__(self) :
    self._hash = None

class CalcNodeValue(CalcNode) :
  def __init__(self, v) :
    super().__init__()
    self.value = v

  def evaluate(self, currentS, parmaMap) :
    return self.value

  def __eq__(self, p) :
    if not isinstance(p, CalcNodeValue): return False
    return self.value == p.value

  def __hash__(self) :
    if self._hash == None :
      h = 17
      h = h * 31 + hash(self.value)
      self._hash = h
    return self._hash

  def __str__(self) :
    return str(self.value)

# we should have a special eval for this and this should be used for discretisation only
class CalcNodeTime(CalcNode) :
  def __init__(self) :
    super().__init__()

  def evaluate(self, currentS, paramMap) :
    return currentS.funcs[str(self)]

  def __eq__(self, p) :
    return isinstance(p, CalcNodeTime)

  def __hash__(self) :
    if self._hash == None :
      self._hash = hash("#t")
    return self._hash

  def __str__(self) :
    return "#t"

"""
class CalcNodeFunc(CalcNode) :
  def __init__(self, f) :
    self.func = f

  # no - this needs changed..
  def evaluate(self, currentS, parmaMap) :
    prop = self.funcinstantiatePred(parmaMap, self.func.prop)
    return currentS.funcs[prop]

  def __str__(self) :
    return str(self.func)
"""
class CalcNodeFunc(CalcNode) :
  def __init__(self, f) :
    super().__init__()
    self.func = f

  def evaluate(self, currentS, parmaMap) :
    prop = self.func.instantiate(parmaMap)
    return currentS.funcs[prop]

  def __eq__(self, p) :
    if not isinstance(p, CalcNodeFunc): return False
    return self.func == p.func

  def __hash__(self) :
    if self._hash == None :
      self._hash = hash(self.func)
    return self._hash  

  def __str__(self) :
    return str(self.func)

class CalcNodeBinaryFunc(CalcNode) :
  evalFs = {"+": (lambda e: e[0] + e[1]),
            "-": (lambda e: e[0] - e[1]),
            "*": (lambda e: e[0] * e[1]),
            "/": (lambda e: e[0] / e[1])
           }

  def __init__(self, rel, lhs, rhs) :
    super().__init__()
    self.rel = rel
    self.lhs = lhs
    self.rhs = rhs

  def evaluate(self, currentS, parmaMap) :
    lhsV = self.lhs.evaluate(currentS, parmaMap)
    rhsV = self.rhs.evaluate(currentS, parmaMap)

    return CalcNodeBinaryFunc.evalFs[self.rel]((lhsV,rhsV))

  def __eq__(self, p) :
    if not isinstance(p, CalcNodeBinaryFunc): return False
    return self.rel == p.rel and self.lhs == p.lhs and self.rhs == p.rhs

  def __hash__(self) :
    if self._hash == None :
      h = 17
      h = h * 31 + hash(self.rel)
      h = h * 31 + hash(self.lhs)
      h = h * 31 + hash(self.rhs)
      self._hash = h
    return self._hash

  def __str__(self) :
    return "(" +self.rel + " " + str(self.lhs) + " " + str(self.rhs) + ")"

    

class Predicate :
  def __init__(self, name = "") :
    self.name = name
    self.vars = []
    self.negated = False
    self._hash = None

  def negate(self) :
    self.negated = True

  def add_var(self, var) :
    self.vars.append(var)

  def key_str(self, pos) :
    return "("+str(pos)+","+str(self)+")"
	
  def instantiate(self, paramMap) :
    return instantiatePred(paramMap, self)
  
  def predicate_equality(self, pred) :
    if not pred.name == self.name :
      return False
    if not len(pred.vars) == len(self.vars) :
      return False
    for i in range(len(self.vars)) :
      if not self.vars[i] == pred.vars[i] :
        return False
    return True

  def abstract_pred(self, type_var) :
    ab_pred = Predicate(self.name)
    l = []
    for var in self.vars :
      ab_pred.add_var(type_var[var])
    return ab_pred
        
  def abstract_pred_from_action(self, action) :
    ab_pred = Predicate(self.name)
    for v in self.vars :
      for i in range(len(action.parameters)) :
        if action.parameters.param_list[i] == v :
          ab_pred.add_var(action.parameters.type_list[i])
          break
        else : print ("abstracting with incompatible action")
    return ab_pred

  def equals (self, pred) :
    if not self.name == pred.name : return False
    if not len(self.vars) == len(pred.vars) : return False
    for i in range(len(self.vars)) :
      if not self.vars[i] == pred.vars[i] : return False
    return True

  def __eq__(self, p) :
    if not isinstance(p, Predicate): return False
    if not p == None and p.name == self.name:
      for (a1,a2) in zip(self.vars, p.vars):
        if not a1 == a2:
          return False
      return True
    return False

  def __hash__(self) :
    if self._hash == None :
      try:
        self._hash = hash(tuple([self.name]+self.vars))
      except:
        self._hash = hash(tuple((self.name,)+self.vars))
    return self._hash

  def __len__(self) :
    return len(self.vars)

  def pddl_str(self, brackets=True) :
    p=self.name + {True:" ",False:""}[len(self.vars)>0] + " ".join(map(lambda x: str(x), self.vars))
    if brackets:
      p = "("+p+")"
    return p

  def __str__(self) :
    return self.pddl_str()


class Proposition(object) :
  def __init__(self, name, args) :
    self.name = name
    self.args = args
    self._hash = None

  def instantiate(self, paramMap=None) :
    return self

  def __eq__(self, p) :
    if not isinstance(p, Proposition): return False
    if not p == None and p.name == self.name:
      for (a1,a2) in zip(self.args, p.args):
        if not a1 == a2:
          return False
      return True
    return False

  def __hash__(self) :
    if self._hash == None :
      try:
        self._hash = hash(tuple([self.name]+self.args))
      except:
        self._hash = hash(tuple((self.name,)+self.args))
    return self._hash
  def pddl_str(self, brackets=True) :
    p=self.name + " " + " ".join(self.args)
    if brackets:
      p = "("+p+")"
    return p
  def __str__(self) :
    #return self.name + " " + " ".join(self.args)
    return self.pddl_str()

class State(object):
  def __init__(self) :
    self.props = []
    self.funcs = {}
    self.tils = []
    self._hash = None

  def clone(self):
    s = State()
    s.props = self.props[:]
    for k,v in self.funcs.items() :
      s.funcs[k] = v
    return s

  def __hash__(self) :
    if self._hash == None:
      s1 = hash(";".join(sorted(map(lambda p: str(p), self.props))))
      s2 = hash(";".join(sorted(map(lambda e: str(e[0]) + ":" + str(e[1]), self.funcs.items()))))
      self._hash = hash(s1) + 13 * hash(s2)
    return self._hash

  def __eq__(self, s) :
    for p in self.props:
      if not p in s.props:
        return False
    for p in s.props :
      if not p in self.props:
        return False
    for k,v in self.funcs.items() :
      if not k in s.funcs or not s.funcs[k]==v:
        return False
    for k,v in s.funcs.items() :
      if not k in self.funcs or not self.funcs[k]==v:
        return False
    return True

  def __str__(self) :
    return ";; State\n;Propositions:\n" + "\n".join(map(lambda x: str(x), self.props)) + "\n;functions:\n" + "\n".join(map(lambda e: "(= " + str(e[0]) + " " + str(e[1]) + ")", self.funcs.items()))
    
"""
class PlanStep(Predicate) :
  def __init__(self, name, t=-1, d=0) :
    super(PlanStep,self).__init__()
    self.time = t
    self.duration = d

  def __str__(self) :
    timeStr = ""
    durStr = ""
    if not t == -1:
      timeStr = str(self.time) + ": "
      durStrg = " [" + str(self.duration) + "]"
    return timeStr + "(" +Predicate.__str__(self) + ")" + durStr
    
"""

"""
Holds two lists of ordered strings. One is for variables and the other for the types of those
variables. 
"""

class ParameterList :
    def __init__ (self, name = "") :
        self.name = name
        self.type_list = []
        self.param_list = []

    def set_name(self, name) : self.name = name

    def add_parameter(self, params) :
        self.type_list, self.param_list = params
    
    def typed_param_list(self) :
      return " ".join(map(lambda e: str(e[0]) + " - " + str(e[1]),zip(self.param_list, self.type_list)))

    def predicate_str(self) :
      return "(" + str(self.name) + " " + self.typed_param_list() + ")"

    def __len__(self) :
        return len(self.type_list)
    def __eq__(self, pl):
      return pl.name == self.name and pl.type_list == self.type_list and pl.param_list == self.param_list
    def __str__(self) :
        return ":" + str(self.name) + " (" + self.typed_param_list() + ")"

"""
Gathers all the features of a pddl action. 
"""



class Action_old :
    def __init__ (self, name = "") :
        self.name = name
        self.parameters = []
        self.negative_preconditions = []
        self.pos_effects = []
        self.neg_effects = []
        self.preconditions = []
        self.action_cost = None

    def add_parameters(self, parameters) :
        self.parameters = parameters

    def set_effect_positive(self, effects) :
        self.pos_effects = effects

    def set_effect_negative(self, effects) :
        self.neg_effects = effects

    def set_precondition_positive(self, preconditions) :
        self.preconditions = preconditions

    def set_precondition_negative(self, preconditions) :
        self.negative_preconditions = preconditions
    
    def add_action_cost(self, cost) :
      self.action_cost = cost

    def get_types(self) :
        d = {}
        for i in range(len(self.parameters)) :
            d[self.parameters.param_list[i]] = self.parameters.type_list[i]
        return d
        
    def get_type(self, var) :
        for i in range(len(self.parameters)) :
            if self.parameters.param_list[i] == var :
                return self.parameters.type_list[i]
                
    def get_pos(self, var) :
        for i in range(len(self.parameters)) :
            if self.parameters.param_list[i] == var :
                return i

    def __str__(self) :
        s = "  (:action " + self.name + "\n    "
        s += str(self.parameters) + "\n    "
        s += ":precondition\n    (and\n"
        for pre in self.preconditions :
            s += "      (" + str(pre) + ")\n"
        s += "    )\n    :effect\n   (and\n"
        for p in self.pos_effects :
            s += "      (" + str(p) + ")\n"
        for n in self.neg_effects :
            s += "      (not (" + str(n) + "))\n"
        if not self.action_cost == None :
          s += "      (increase (total-cost) " + str(self.action_cost)+ ")\n"
        return s + "  ))"


class Action(object) :
    def __init__ (self, name = "") :
        self.name = name
        self.parameters = ParameterList("parameters")
        self.precondition = None
        self.effect = None
        self.action_cost = None
    

    def add_parameters(self, parameters) :
        self.parameters = parameters

    def set_effect(self, effect) :
        self.effect = effect
        self.isContinuous = self._inTermsOfTime(effect)

    def _inTermsOfTime(self, node) :
        if node.__class__ == ConjEffect :
            if len(node.conj) > 0:
              return reduce(lambda e: e[0] or e[1], map(lambda x: self._inTermsOfTime(x), node.conj))
            return False
        elif node.__class__ in (NegPropAssign,PropAssign) :
            return False # can't be referring to time
        elif node.__class__ in (FuncAssign,FuncIncrease,FuncDecrease):
            return self._inTermsOfTime(node.rhs)
        elif node.__class__ == CalcNodeTime :
            return True
        elif node.__class__ == CalcNodeValue :
            return False
        elif node.__class__ == CalcNodeBinaryFunc :
            return self._inTermsOfTime(node.lhs) or self._inTermsOfTime(node.lhs)
        elif node.__class__ == CalcNodeFunc :
            return False
        #else :
        #    print "Forgotten continuous action check node type? ", node, node.__class__

    def add_action_cost(self, cost) :
        self.action_cost = cost

    def set_precondition(self, precondition) :
        self.precondition = precondition

    def get_types(self) :
        d = {}
        for i in range(len(self.parameters)) :
            d[self.parameters.param_list[i]] = self.parameters.type_list[i]
        return d
        
    def get_type(self, var) :
        for i in range(len(self.parameters)) :
            if self.parameters.param_list[i] == var :
                return self.parameters.type_list[i]
                
    def get_pos(self, var) :
        for i in range(len(self.parameters)) :
            if self.parameters.param_list[i] == var :
                return i

    def apply(self, s, param_map):
      ns = s.clone()
      self.effect.apply(s, ns, param_map)
      return ns

    def clone(self, suffix=""):
      a = Action(self.name+suffix)
      if self.parameters:
        a.parameters = ParameterList("parameters")
        a.parameters.param_list = self.parameters.param_list
        a.parameters.type_list = self.parameters.type_list
      try:
        G = self.precondition.conj[:]
      except:
        G = [self.precondition]
      a.precondition = ConjGoal(G)
      try:
        E = self.effect.conj[:]
      except:
        E = [self.effect]
      a.effect = ConjEffect(E)
      return a
  

    def __str__(self) :
        s = "  (:action " + self.name + "\n"
        if self.parameters and len(self.parameters) > 0 :
          s += "    " + str(self.parameters) + "\n"
        else:
          s += "    :parameters ()\n"
        if self.precondition:
          s += "    :precondition " + self.precondition.__str__() + "\n"
        effStr = "    :effect\n   "
        if not self.action_cost == None :
            effStr += "(and\n    "
            if self.effect.__class__ == ConjEffect :
                effStr += "\n    ".join(map(lambda x: ""+x.__str__(), self.effect.conj))
                effStr += "\n    (increase (total-cost) " + str(self.action_cost)+ ")\n    )"
            else :
                effStr += str(self.effect)
                effStr += "\n    (increase (total-cost) " + str(self.action_cost)+ ")\n    )"
        else :
            effStr += str(self.effect)
        s += effStr
        return s + "\n  )"


class DurativeAction(Action) :
  def __init__(self, name = "") :
    super(DurativeAction, self).__init__(name)
    self.duration = None
    self.at_start_c=list()
    self.at_end_c=list()
    self.over_all_c=list()
    self.at_start_e=list()
    self.at_end_e=list()
    self.continuous_effects = list()

  def clone(self):
    a = DurativeAction(self.name)
    a.parameters = self.parameters
    a.duration = self.duration
    a.at_start_c = self.at_start_c[:]
    a.at_end_c = self.at_end_c[:]
    a.over_all_c = self.over_all_c[:]
    a.at_start_e = self.at_start_e[:]
    a.at_end_e = self.at_end_e[:]
    a.continuous_effects = self.continuous_effects[:]
    return a


  def get_dynamic_predicates(self):
    l = []
    for eff in self.at_start_e + self.at_end_e:
      if isinstance (eff, PropAssign):
        l.append(eff.prop.name)
    return l
  
  def get_dynamic_functions(self):
    l = []
    for eff in self.at_start_e + self.at_end_e:
      if isinstance (eff, FuncAssign):
        l.append(eff.lhs.func.name)
    return l
  
  def __str__(self) :
    s = "  (:durative-action " + self.name + "\n"
    if self.parameters and len(self.parameters) > 0 :
      s += "    " + str(self.parameters) + "\n"
    else:
      s += "    :parameters ()\n"
    if self.duration:
      s += "    :duration " + str(self.duration) + "\n"
    if self.at_start_c or self.at_end_c or self.over_all_c:
      s += "    :condition (and\n"
      if self.at_start_c:
          s += "      " + " ".join(map(lambda e: "(at start " + str(e) + ")", self.at_start_c)) + "\n"
      if self.at_end_c:
          s += "      " + " ".join(map(lambda e: "(at end " + str(e) + ")", self.at_end_c)) + "\n"
      if self.over_all_c:
          s += "      " + " ".join(map(lambda e: "(over all " + str(e) + ")", self.over_all_c)) + "\n"
      s += "    )\n"
    s += "    :effect (and\n"
    if self.at_start_e:
      s += "      " + " ".join(map(lambda e: "(at start " + str(e) + ")", self.at_start_e)) + "\n"
    if self.at_end_e:
      s += "      " + " ".join(map(lambda e: "(at end " + str(e) + ")", self.at_end_e)) + "\n"
    if self.continuous_effects:
      s += "      " + " ".join(map(lambda e: str(e), self.continuous_effects)) + "\n"
    s += "    )\n"
    return s + "\n  )"

class Process(Action) :
  def __init__(self, name = "") :
    super(Process, self).__init__(name)


class Event(Action) :
  def __init__(self, name = "") :
    super(Event, self).__init__(name)


# Current version instantiates at application (reducing some code..)
class InstDiscreteAction(object) :
    def __init__(self, a, prams, time, duration) :
        self.op = a
        self.time=time
        self.duration=duration
        self.parameters=prams

    def apply(self, s) :
        nextS = State()
        nextS.props = s.props[:]; nextS.funcs = dict(s.funcs)
        self.op.effect.apply(s,nextS, dict(zip(self.op.parameters.param_list, self.parameters)))
        return nextS

    def __str__(self) :
        return str(self.time) + ": (" + self.op.name + " " + " ".join(self.parameters) + ")" + " [" + str(self.duration)+"]"

class InstDiscreteProcess(InstDiscreteAction) :
  def __init__(self, a, prams, time, duration) :
    super(InstDiscreteProcess, self).__init__(a, prams, time, duration)


class InstEvent(InstDiscreteAction) :
  def __init__(self, a, prams, time, duration) :
    super(InstEvent, self).__init__(a, prams, time, duration)


class InstContinuousAction(InstDiscreteAction) :
  def __init__(self, a, prams, time, duration) :
    super(InstContinuousAction, self).__init__(a, prams, time, duration)

  #def apply(self, s) :
  #  pass

class InstContinuousProcess(InstContinuousAction) :
  def __init__(self, a, prams, time, duration) :
    super(InstContinuousProcess, self).__init__(a, prams, time, duration)

class PlanAction:
  def __init__(self, time, op, args, duration):
    self.time = time
    self.duration = duration
    self.predicate = op
    self.arguments = args

  def clone(self):
    return PlanAction(self.time, self.predicate, self.arguments[:], self.duration)

  def __str__(self):
    return "{}: ({} {}) [{}]".format(
        self.time, self.predicate, " ".join(self.arguments), self.duration
    )

"""
Gathers all the aspects of a domain into a single class. 
"""

class Domain :
    def __init__(self) :
        self.name = ''
        self.actions = []
        self.events = []
        self.processes = []
        self.requirements = []
        self.types = []
        self.predicates = []
        self.functions = []
        self.constants = {}
        self.invariant_preds = []
        self.has_action_costs = False

    def set_name(self, name) :
        self.name = name

    def add_action(self, action) :
        self.actions.append(action)
    
    def add_event(self, event) :
        self.events.append(event)
    
    def add_process(self, process) :
        self.processes.append(process)

    def add_requirement(self, requirement) :
        self.requirements.append(requirement)

    def add_constants(self, constants) :
        self.constants += constants

    def add_type(self, types) :
        self.types += types

    def add_predicate(self, predicate) :
        self.predicates.append(predicate)
        
    def add_function(self, function):
        self.functions.append(function)

    def get_dynamic_predicates(self):
      dps = set()
      for action in self.actions:
        dps.update(action.get_dynamic_predicates())
      return list(dps)

    def get_dynamic_functions(self):
      dfs = set()
      for action in self.actions:
        dfs.update(action.get_dynamic_functions())
      return list(dfs)
        

    def transitions(self, problem) :
        d = self.type_and_property_trails(problem)
        trans = {}
        for k in d.keys() :
            trans[k] = []
            for e in d[k] :
                action, precs, pos_effs, neg_effs = e
                start = self.start_state(precs, neg_effs)
                end = self.end_state(precs, pos_effs, neg_effs)
                trans[k].append((action, start, end))
        return trans

    """
    Add a trail entry to a dictionary
    """
    def append_trail_to_all(self, d, l, action, precs, pos_effs, neg_effs) :
        for e in l :
            if not (d.has_key(e)) :
                d[e] = []
            d[e].append((action, precs, pos_effs, neg_effs))
                

    def find_var_in_pred(self, var, pred) :
        l = []; j = -1
        for i in range(len(pred)) :
            if pred.vars[i] == var :
                j = i
                break
        return j
    
    def find_operator(self, op_name) :
      for op in self.actions:
        if op_name == op.name :
          return op
      return None

    def extend_with_action_costs(self) :
      if not self.has_action_costs :
        self.has_action_costs = True
        self.requirements.append(":action-costs")

    def getTopperStr(self) :
      s = "(define (domain " + self.name + ")\n  "
      if len(self.requirements) > 0 :
        s += "(:requirements\n"
        for req in self.requirements :
          s+= " " + req
        s += "  )\n"
      if len(self.types) > 0 :
        s += "\n  (:types\n"
        for i in range(len(self.types[1])) :
          s += "    " + str(self.types[1][i]) + " - " + str(self.types[0][i]) + "\n"
        #for i in range(len(self.types[1])) :
        #  if not str(self.types[0][i])=="object":
        #    s += "    " + str(self.types[1][i]) + " - " + str(self.types[0][i]) + "\n"
        #for i in range(len(self.types[1])) :
        #  if str(self.types[0][i])=="object":
        #    s += "    " + str(self.types[1][i]) + " - " + str(self.types[0][i]) + "\n"
        s += "  )\n"
      if len(self.constants) > 0 :
        s += "  (:constants\n"
        for (k,v) in self.constants.iteritems() :
          s += "    " + k + " - " + v + "\n"
        s += "  )\n"
      s+= "  (:predicates\n"
      for predicate in self.predicates :
        s += "    " + predicate.predicate_str() + "\n"
      s+= "  )\n"
      if self.functions :
        s+= "  (:functions\n"
        for functions in self.functions :
          s += "    " + functions.predicate_str() + "\n"
        s+= "  )\n"
      return s

    def __str__(self) :
      s = "(define (domain " + self.name +")"#+ "\n  (:requirements:"
      if len(self.requirements) > 0 :
        s += "  (:requirements\n"
        for req in self.requirements :
          s+= "    :" + req + "\n"
        s += "  )\n"
      if self.types :
        s += "\n  (:types\n"
        for i in range(len(self.types[1])) :
          s += "    " + str(self.types[1][i]) + " - " + str(self.types[0][i]) + "\n"
        s += "  )\n"
      s += "  (:predicates\n"
      for predicate in self.predicates :
        s += "    " + predicate.predicate_str() + "\n"
      s+= "  )\n"
      if self.functions :
        s+= "  (:functions\n"
        for functions in self.functions :
          s += "    " + functions.predicate_str() + "\n"
        s+= "  )\n"
      elif self.has_action_costs :
        s += "  (:functions (total-cost) - number)\n"
      s += "\n"
      for action in self.actions :
        s += str(action) + "\n"
      return s + ")"

class Problem :

  def __init__ (self) :
    self.name = ""
    self.domain = ""
    self.objects = {}
    self.initial_state = []
    self.goal = None
    self.metric=None

  def set_name(self, name) :
    self.name = name

  def set_domain(self, domain) :
    self.domain = domain

  def set_objects(self, objects) :
    self.objects = objects

  def add_objects(self, d) :
    for k,v in d.items() :
      self.objects[k] = v

  def set_initial_state(self, state) :
    self.initial_state = state

  def set_goal_state(self, state) :
    self.goal = state
    
  def __str__ (self) :
    if "str" in self.__dict__:
      return self.str
    return self.name

class Metric(object):
  pass
class Minimisation(Metric):
  def __init__(self, f):
    self.f = f
  def __str__(self):
    return "(:metric minimize "+str(self.f) +")"
class Maximisation(Metric):
  def __init__(self, f):
    self.f = f
  def __str__(self):
    return "(:metric maximize "+str(self.f) +")"
class Duration(object):
  def __init__(self, rhs):
    self.rhs = rhs
  def __str__(self):
    return "(= ?duration " + str(self.rhs) +")"
class VariableDuration(object):
  def __init__(self, exp):
    self.exp = exp
  def __str__(self):
    return str(self.exp)

