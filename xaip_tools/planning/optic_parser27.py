import re

from ..pddl_resources import planning_types

LAST_TIME=None

def parse_tamer(s):
  plan = []
  for l in s.split("\n"):
    l = l.split(";")[0].strip()
    if ":" in l:
      plan.append(l)
  pattern = r'(\d+\.\d+):\s+\(([^)]+)\)\s+\[(\d+)\]'
  plan_actions = []
  for line in plan:
    match = re.match(pattern, line)
    if match:
      time = float(match.group(1))
      action_parts = match.group(2).split()
      op = action_parts[0]
      args = action_parts[1:]
      duration = float(match.group(3))
      plan_action = planning_types.PlanAction(time, op, args, duration)
      plan_actions.append(plan_action)
  return plan_actions

def record_time(t):
  global LAST_TIME
  LAST_TIME=t

def parse_optic(optic_output_str, code_ret=False):

    #print ("LUMP START!=================================")
    #print (optic_output_str)
    #print ("LUMP END!=================================")

    # Regular expression pattern for a line
    if optic_output_str.__class__ == bytes:
      optic_output_str = optic_output_str.decode('ascii')
    pattern = r"\d+\.\d+: \(.*?\)  \[[\d.]+\]"
    time_pattern = r"; Time (\d+\.\d+|\d+)"

    # Split the text into lines
    lines = optic_output_str.split('\n')

    plan = []
    last_plan = None
    plan_found = False
    unsolvable=False
    # Iterate through the lines
    state0=False
    t=None
    for i,line in enumerate(lines):
        # Check if the line matches the pattern
        if not plan_found and "; Plan found with metric" in line:
          plan_found=True
        if ";; Problem unsolvable!" in line or "; Goals unreachable from the initial state" in line :
          unsolvable=True
        if "As such, the problem has been deemed" in line:
          state0=True
        if state0 and line.startswith("unsolvable."):
          unsolvable=True
        time_match = re.search(time_pattern, line)
        if time_match:
          t = time_match.group(1)
          
        if re.match(pattern, line):
            # Process the line (e.g., append it to the plan list)
            plan.append(line)
        #elif line.startswith(" * All goal deadlines now no later than"):
        else:
            if i == len(lines)-1: continue
            # The pattern doesn't match, so exit the loop
            if len(plan) > 0:
                last_plan = plan
                plan = []
    record_time(t)
    # If there's no explicit last plan, use the last one found
    if plan_found :
      if not last_plan:
        last_plan = plan

      plan_actions = []

      # Regular expression pattern to match the line format
      pattern = r'(\d+\.\d+): \((.*?)\)  \[(\d+\.\d+)\]'

      # Iterate through the lines and parse them into PlanAction objects
      for line in last_plan:
        match = re.match(pattern, line)
        if match:
          time = float(match.group(1))
          action_parts = match.group(2).split()
          op = action_parts[0]
          args = action_parts[1:]
          duration = float(match.group(3))
          plan_action = planning_types.PlanAction(time, op, args, duration)
          plan_actions.append(plan_action)
      return plan_actions
    if code_ret:
      if unsolvable: return -1
      return 0

def parse_action(s):
  bits = s[1:-1].split(" ")
  return planning_types.PlanAction(-1, bits[0], bits[1:], -1)
def parse_instantiated_actions(text):
  lines = text.split('\n')
  action_lines = []
  reading=False
  for line in lines:
    if "@" in line:
      if reading:
        break
      else:
        reading = True
    elif reading:
      action_lines.append(line.strip())
  return list(map(lambda a: parse_action(a), action_lines))

