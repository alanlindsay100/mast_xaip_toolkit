import yaml

class op_template:
  def __init__(self, op, verbs):
    self.op = op
    self.verbs = verbs

class action_template:
  def __init__(self, op, params, description):
    self.op_sym_m = op
    self.param_sym_m = params
    self.description = description

class param_template:
  def __init__(self, param, pid, objs, preps):
    self.param = param
    self.param_id = pid
    self.objs = objs
    self.preps = preps

def _parse_list(s):
  if s:
    return list(map(lambda x: x.strip(), s.split(",")))
  return []

def parse_action_templates(fn, preds, M):
  f = open(fn, 'r')
  data = list(yaml.load_all(f, Loader=yaml.FullLoader))

  # Initialize a list to store op_templates
  op_templates = []

  pred_map = dict(map(lambda x: (x.name, x), preds))

  # Iterate through each action_template entry in the file
  for action_data in data:
    action = action_data["action_template"]
    op_data = action['op']
    x = op_data['operator_symbols']
    op_sym = pred_map[x]
    verbs = _parse_list(op_data['verb_alternatives'])
    op = op_template(op=op_sym, verbs=verbs)
    num_params = len(list(filter(lambda x: x.startswith("parameter"), action.keys())))
    param_templates = []
    for i in range(1, num_params+1):
      param_data = action['parameter' + str(i)]
      param = param_data['variable']
      param_id = i-1
      objs = list(map(lambda e: e[0], filter(lambda e: e[1]==param_data['type'], M[1].objects.items())))
      preps = list(map(lambda x: x.split(" "), _parse_list(param_data['prepositions'])))
      pt = param_template(param=param, pid=param_id, objs=objs, preps=preps)
      param_templates.append(pt)
    description = action['description']
    op_templates.append(action_template(op=op, params=param_templates, description=description))
  return op_templates

