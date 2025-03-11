
"""
  Alan Lindsay
"""
from .planning_types import *

def isFloat(s) :
    try:
        float(s)
        return True
    except:
        return False

class S_Expression :

    """
    Adapted from Elliott Franco Drabek

    This moves through each line and yields brackets and data as it moves. It removes all spaces.
    It automatically yields a bracket on its own. However will gather a full sequence of characters
    before yielding, when no bracket or space exists.
    """

    def generate_tokens(self, s, no_space = True):
        for line in s:
            line = line.split(";")[0]
            line_len = len(line)
            left = 0

            while left < line_len:
                c = line[left]
                # remove spaces
                if (c.isspace() and no_space) :
                    left += 1
                # report brackets
                elif c in '()':
                    yield c
                    left += 1
                # capture chunks of text
                else:
                    right = left + 1
                    while right < line_len:
                        c = line[right]
                        if (c.isspace() and no_space) or c in '()':
                            break
                        right += 1

                    token = line[left:right].strip().lower()
                    if token.isdigit():
                        token = int(token)
                    elif isFloat(token) :
                        token = float(token)
                    yield token
                    # start where the chunk ended. 
                    left = right



    """
    Read all produces a hierarchy list structure. It uses two variables stack and path to collect all
    of the information. Stack is used to refer to the place where data is being added so as brackets
    are opened, it disappears into deeper nested lists. Path is used to remember where it has been and
    is used when brackets are closed and stack must return back a level. With correctly matching 
    brackets stack will refer to the bottom of the structure by the end.

    """

    def read_all(self, s):
        stack = []
        path = []
        for token in self.generate_tokens(s):
            if token == '(':
                path.append(stack)  # hold reference to this layer
                a = [] 
                stack.append(a)     # new list added to the stack
                stack = a           # add to new list
            elif token == ')':
                stack = path[-1]    # move out one layer
                del path[-1]        # remove this layer from the path
            else:
                stack.append(token) # add sequence of characters
        return stack


class PddlParser :

    def __init__(self) :
        self.parder = S_Expression()

    """
    Get the string in as a nested list.
    For each section of the description, choose the correct parser and
    pass the list to be parsed and the object to be added to.
    """

    def separate(self, s, o) :
        l = self.parder.read_all(s)
        for e in l[0] :
            if not '\xef' in e and not '\xbb' in e and not '\xbf' in e:
                if e[0] in self.dict:
                  self.dict[e[0]](e[1:], o)
                else:
                  print ("WARNING: ignoring unknown section: ", e[0])

    def parse_name(self, name, problem) :
        problem.set_name(name[0])

    def parse_pass(self, n, p) :
        pass

    ## Util ##

    """
    This method turns a list of the form ((x y - z a b d - c), (e - f)) into two lists, one for types and the other for
    names: (z, c, f) and (x, y, a, b, d, e)
    """

    def list_to_types_and_labels(self, predicate) :
        l = []; types = []; vars = []; b = False
        if not '-' in predicate :
          predicate.append('-')
          predicate.append('object')
        for var in predicate :
            if b :
                for e in l :
                    types.append(var)
                    vars.append(e)
                    b = False
                    l = []
            elif var == '-' :
                b = True
            else : 
                l.append(var)
        return types, vars

    """
    This method takes a list of with a formula, for example: (and (not (pred1 b c)) (pred2 s) (pred3 x y)) and
    translates it into separate Predicate objects adding them to either the positive or negative function, depending how 
    the negation transpires. Will only work for 'and' and 'not'.
    """

    def list_to_predicates(self, l, preds_neg, preds_pos, neg = False) :
        sym = l[0]
        if sym == "and" :
            for e in l[1:] :
                self.list_to_predicates(e, preds_neg, preds_pos, neg)
        elif sym == "not" :
            self.list_to_predicates(l[1], preds_neg, preds_pos, (not neg))  
        else :
            if neg : preds_neg.append(self.phrase_to_predicate(l))
            else : preds_pos.append(self.phrase_to_predicate(l))
    
    """
    Used by list_to_predicate. Takes a predicate phrase and makes a new predicate from it and returns the predicate.
    """    

    def phrase_to_predicate(self, phrase) :
        pred = Predicate(phrase[0])
        for e in phrase[1:] :
            pred.add_var(e)
        return pred


    def parseGoal(self, l) :
        sym = l[0]
        if sym == "and" :
            conj = []
            for e in l[1:] :
                conj.append(self.parseGoal(e))
            return ConjGoal(conj)
        if sym == "or" :
            conj = []
            for e in l[1:] :
                conj.append(self.parseGoal(e))
            return DisjunctGoal(conj)
        if sym == "not" :
            return self.parseGoalProp(l[1], False)

        inEqs = [">", "<", "=", "<=", ">=", "!="]

        if sym in inEqs :
            lhs = self.parseFuncExp(l[1])
            rhs = self.parseFuncExp(l[2])
            return CalcNodeBinaryRel(sym, lhs, rhs)

        return self.parseGoalProp(l, True)

    def parseFuncExp(self, fexp) :
        if fexp.__class__ == int or fexp.__class__ == float :
          return CalcNodeValue(fexp)
        if fexp == "#t" :
          return CalcNodeTime()
        
        rel = fexp[0]

        if rel in ("+", "-", "*", "/"):
            return CalcNodeBinaryFunc(rel, self.parseFuncExp(fexp[1]), self.parseFuncExp(fexp[2]))
        
        return self.parseFunc(fexp)


class PddlDomainParser(PddlParser) :

    def __init__ (self) :
        PddlParser.__init__(self)
        self.dict = { 'domain' :        self.parse_name,
                      'd' :             self.parse_pass,
                      ':requirements' : self.parse_requirements,
                      ':types' :        self.parse_types,
                      ':constants' :  self.parse_constants,
                      ':predicates' :   self.parse_predicates,
                      ':action' :       self.parse_action,
                      ':durative-action' : self.parse_durative_action,
                      ':process' :      self.parse_process,
                      ':event' :      self.parse_event,
                      ':functions' :    self.parse_functions,
                    }

    def parse(self, s) :
        domain = Domain()
        self.separate(s, domain)
        return domain

	
    """
    The structure of each part of the domain description is different. 
    These methods parse the individual parts separately. 
    """
    
    def parse_nothing(self, stuff, problem) :
        pass
    
    
    def parse_constants(self, constantStr, problem) :
        d = {}
        b = False
        const_list = []
        for o in constantStr :
            if b :
                b = False
                for obj in const_list :
                    d[obj] = o
                const_list = []
            elif o == "-" :
                b = True
            else :
                const_list.append(o)
        if len(d) == 0 :
          for o in objects :
            d[o] = "object"
        problem.add_constants(d)

    def parse_requirements(self, requirements, problem) :
        for r in requirements :
            problem.add_requirement(r[1:])

    def parse_types(self, types, problem) :
        var_type_list = self.list_to_types_and_labels(types)
        problem.add_type(var_type_list)    

    def parse_predicates(self, predicates, problem) :
        for predicate in predicates :
            pred = ParameterList(predicate[0])
            pred.add_parameter(self.list_to_types_and_labels(predicate[1:]))
            problem.add_predicate(pred)
    def parse_functions(self, functions, problem) :
        for f in functions:
            if f == "-" or f =="number": continue
            pred = ParameterList(f[0])
            pred.add_parameter(self.list_to_types_and_labels(f[1:]))
            problem.add_function(pred)
    def parse_action(self, action_list, model) :
        action = Action(action_list[0])
        self.parse_transition(action, action_list)
        model.add_action(action)
        
    def parse_durative_action(self, action_list, model) :
        action = DurativeAction(action_list[0])
        self.parse_durative_transition(action, action_list)
        model.add_action(action)
        
    def parse_process(self, action_list, model) :
        process = Process(action_list[0])
        self.parse_transition(process, action_list)
        model.add_process(process)
    
    def parse_event(self, action_list, model) :
        event = Event(action_list[0])
        self.parse_transition(event, action_list)
        model.add_event(event)

    def parseGoalProp(self, l, pos) :
        p = self.phrase_to_predicate(l)
        if pos: return PropGoal(p)
        return NegPropGoal(p)

    def parseProp(self, l, pos) :
        p = self.phrase_to_predicate(l)
        if pos: return PropAssign(p)
        return NegPropAssign(p)

    def parseFunc(self, f) :
        p = self.phrase_to_predicate(f)
        return CalcNodeFunc(p)

    def parseConditional(self, c):
      lhs = self.parseGoal(c[0])
      rhs = self.parseEffect(c[1])
      ceff = ConditionalEffect(lhs, rhs)
      return ceff

    def parseOneof(self, c):
      lhs = self.parseEffect(c[0])
      rhs = self.parseEffect(c[1])
      ceff = OneOfEffect(lhs, rhs)
      return ceff

    def parseEffect(self, l) :
        sym = l[0]
        if sym == "and" :
            conj = []
            for e in l[1:] :
                conj.append(self.parseEffect(e))
            return ConjEffect(conj)
        if sym == "not" :
            return self.parseProp(l[1], False)
        if sym == "when" :
            return self.parseConditional(l[1:])
        if sym == "oneof" :
            return self.parseOneof(l[1:])
            
        funcClass = {"assign": FuncAssign, "increase": FuncIncrease, "decrease": FuncDecrease}
        if sym in funcClass.keys() :
            lhs = self.parseFunc(l[1])
            rhs = self.parseFuncExp(l[2])
            return funcClass[sym](lhs, rhs)
        
        return self.parseProp(l, True)


    """def parseGoal(self, l) :
        sym = l[0]
        if sym == "and" :
            conj = []
            for e in l[1:] :
                conj.append(self.parseGoal(e))
            return ConjGoal(conj)
        if sym == "not" :
            return self.parseGoalProp(l[1], False)

        inEqs = [">", "<", "=", "<=", ">=", "!="]

        if sym in inEqs :
            lhs = self.parseFuncExp(l[1])
            rhs = self.parseFuncExp(l[2])
            return CalcNodeBinaryRel(sym, lhs, rhs)

        return self.parseGoalProp(l, True)
   """
    def parse_transition(self, transition, action_list) :
        label = ""
        for e in action_list[1:] :
            if type(e) == type([]) :
                if label == "parameters" :
                    pred = ParameterList(label)
                    pred.add_parameter(self.list_to_types_and_labels(e))
                    transition.add_parameters(pred)
                elif label == "precondition" :
                    transition.set_precondition(self.parseGoal(e))
                elif label == "effect" :
                    transition.set_effect(self.parseEffect(e))
                else :
                    print ("Wrongly labelled transition: " + action_list[0])
            else: label = e[1:]

    def parse_durative_transition(self, transition, action_list) :
        label = ""
        for e in action_list[1:] :
            if type(e) == type([]) :
                if label == "parameters" :
                    pred = ParameterList(label)
                    pred.add_parameter(self.list_to_types_and_labels(e))
                    transition.add_parameters(pred)
                elif label == "duration" :
                    sym = e[0]
                    assert e[0] in ("=","<=",">=") and e[1]== "?duration"
                    rhs = self.parseFuncExp(e[2])
                    if sym == "=": transition.duration = Duration(rhs)
                    else: transition.duration = VariableDuration(CalcNodeBinaryRel(sym, CalcNodeValue("?duration"), rhs))
                elif label == "condition" :
                    assert e[0] == "and"
                    ac={"over all": transition.over_all_c,
                        "at start": transition.at_start_c,
                        "at end": transition.at_end_c}
                    for entry in e[1:]:
                      tok = entry[0] +" "+ entry[1]
                      if tok in ac:
                        ac[tok].append(self.parseGoal(entry[2]))
                      else:
                        print ("WARNING: wrong condition label? " + str(tok))
                elif label == "effect" :
                    assert e[0] == "and"
                    ae={"at start": transition.at_start_e,
                        "at end": transition.at_end_e}
                    for entry in e[1:]:
                      if entry[0] in ("increase", "decrease"):
                        transition.continuous_effects.append(self.parseEffect(entry))
                      else:
                        tok = entry[0] +" "+ entry[1]
                        if tok in ae:
                          ae[tok].append(self.parseEffect(entry[2]))
                        else:
                          print ("WARNING: wrong effect label? " + str(tok))
                else :
                    print ("Wrongly labelled transition: **" + label + " => " + action_list[0])
            else: label = e[1:]


class PddlProblemParser(PddlParser) :

    def __init__ (self) :
        PddlParser.__init__(self)
        self.object_list = []
        self.dict = {':domain' :       self.parse_domain,
                     'problem' :       self.parse_name,
                     'd'       :       self.parse_pass,
                     ':requirements' : self.parse_pass,
                     ':metric' : self.parse_metric,
                     ':objects':       self.parse_objects,
                     ':init'   :       self.parse_initial_state,
                     ':goal'   :       self.parse_goal_state
                    }

    def parse(self, s) :
        problem = Problem()
        self.separate(s, problem)
        return problem


    """
    The structure of each part of the domain description is different. 
    These methods parse the individual parts separately. 
    """

    def parse_domain(self, domain, problem) :
        problem.set_domain(domain[0])

    def parse_objects(self, objects, problem) :
        d = {}
        b = False
        for o in objects :
            if b :
                b = False
                for obj in self.object_list :
                    d[obj] = o
                self.object_list = []
            elif o == "-" :
                b = True
            else :
                self.object_list.append(o)
        if len(d) == 0 :
          for o in objects :
            d[o] = "object"
        problem.add_objects(d)

    def parse_initial_state(self, initial_state, problem) :
      problem.set_initial_state(self._parse_initial_state(initial_state))
    
    def parseProp(self, l, pos) :
        p = self.phrase_to_proposition(l)
        if pos: return PropAssign(p)
        return NegPropAssign(p)    
    
    def parseEffect(self, l) :
        sym = l[0]
        if sym == "and" :
            conj = []
            for e in l[1:] :
                conj.append(self.parseEffect(e))
            return ConjEffect(conj)
        if sym == "not" :
            return self.parseProp(l[1], False)
            
        funcClass = {"assign": FuncAssign, "increase": FuncIncrease, "decrease": FuncDecrease}
        if sym in funcClass.keys() :
            lhs = self.parseFunc(l[1])
            rhs = self.parseFuncExp(l[2])
            return funcClass[sym](lhs, rhs)
        
        return self.parseProp(l, True)
    
    def _parse_initial_state(self, initial_state) : # nah this should just be an effect
        state = State()
        for pred in initial_state :
          #print pred
          if pred[0] in ("assign","=") and pred[1].__class__ == list :
            state.funcs[self.phrase_to_proposition(pred[1])] = pred[2]
          elif pred[0] in ("at") and pred[2].__class__ == list :
            i = float(pred[1])
            eff = self.parseEffect(pred[2])
            state.tils.append(TIL(i, eff))
          else :
            state.props.append(self.phrase_to_proposition(pred))
        return state

    def parseFunc(self, f) :
        p = self.phrase_to_proposition(f)
        return CalcNodeFunc(p)

    def phrase_to_proposition(self, phrase) :
        return Proposition(phrase[0], phrase[1:])

    def parse_goal_state(self, goal_state, problem) :
        problem.set_goal_state(self.parseGoal(goal_state[0]))

    def parseGoalProp(self, l, pos) :
        p = self.phrase_to_proposition(l)
        if pos: return PropGoal(p)
        return NegPropGoal(p)

    def parse_metric(self, metric_str, problem):
      if metric_str[0] == "minimize":
        f = self.parseFuncExp( metric_str[1])
        problem.metric = Minimisation(f)
      if metric_str[0] == "maximize":
        f = self.parseFuncExp( metric_str[1])
        problem.metric = Maximisation(f)
      

class PDDLPlanParser(PddlParser) :

    def __init__ (self) :
        PddlParser.__init__(self)

    def parse(self, s, domain) :
        self.domain = domain
        plan = []
        for aline in s:
          self.parseInstAction(aline, plan)
        return plan

    def parseInstAction(self, aline, plan) :
        t,rest=aline.split(":")
        p,dur = rest.split("[")
        a = p.replace("(","").replace(")","").strip().lower().split(" ")
        op = list(filter(lambda x: x.name == a[0], self.domain.actions))[0]
        if op.isContinuous :
          plan.append(InstContinuousAction(op, a[1:], float(t), float(dur.replace("]",""))))
        else :
          plan.append(InstDiscreteAction(op, a[1:], float(t), float(dur.replace("]",""))))


