import yaml, re

from nl2action import op_template, _parse_list
from jug import conjugate




def parse_action_templates(fn):
  f = open(fn, 'r')
  data = list(yaml.load_all(f, Loader=yaml.FullLoader))

  # Initialize a list to store op_templates
  op_templates = []

  # Iterate through each action_template entry in the file
  for action_data in data:
    action = action_data["action_template"]
    op_data = action['op']
    verbs = _parse_list(op_data['verb_alternatives'])
    op_templates.append(op_template(op=op_data['operator_symbols'], verbs=verbs))
  return op_templates


op_templates = parse_action_templates("action_templates.yaml")
for op_template in op_templates:
  print ("==========================================")
  print ("=== " + op_template.op)
  print ("==========================================")
  l = list()
  print (", ".join([v for l in map(lambda v: conjugate(v), op_template.verbs) for v in l]))
    


