import re

from ..pddl_resources import planning_types


# Sample plan text
plan_text = """

; Version LPG-td-1.4
; Seed 23357928
; Command line: /home/al/planners/lpgtd-1_4-linux/LPG-td-1.4/lpg-td -o /home/al/planners/IPC3/Tests1/DriverLog/Time/driverlogTimed.pddl -f /home/al/planners/IPC3/Tests1/DriverLog/Time/pfile3 -cputime 20 -n 10 
; Problem /home/al
; Time 0.01
; Search time 0.01
; Parsing time 0.00
; Mutex time 0.00
; MakeSpan 173.00


0.0003:   (WALK DRIVER2 S0 P2-0) [100.0000]
0.0003:   (LOAD-TRUCK PACKAGE3 TRUCK1 S1) [2.0000]
100.0005:   (WALK DRIVER2 P2-0 S2) [73.0000]
0.0002:   (BOARD-TRUCK DRIVER1 TRUCK1 S1) [1.0000]
2.0008:   (DRIVE-TRUCK TRUCK1 S1 S2 DRIVER1) [55.0000]
57.0010:   (UNLOAD-TRUCK PACKAGE3 TRUCK1 S2) [2.0000]
59.0015:   (DRIVE-TRUCK TRUCK1 S2 S0 DRIVER1) [23.0000]
82.0018:   (LOAD-TRUCK PACKAGE2 TRUCK1 S0) [2.0000]
82.0018:   (LOAD-TRUCK PACKAGE1 TRUCK1 S0) [2.0000]
84.0023:   (DRIVE-TRUCK TRUCK1 S0 S1 DRIVER1) [42.0000]
126.0025:   (UNLOAD-TRUCK PACKAGE1 TRUCK1 S1) [2.0000]
126.0025:   (UNLOAD-TRUCK PACKAGE2 TRUCK1 S1) [2.0000]


"""

def parse_action_str(action):
    # Regular expression pattern to split the action into predicate and arguments
    pattern = r"\((\w+(?:-\w+)*)\s+(.*?)\)"
    match = re.match(pattern, action)
    if match:
        predicate = match.group(1)
        arguments = match.group(2).split()
        return predicate, arguments
    else:
        return None, []

def parse_plan(plan_text):
    # Regular expression pattern to match plan steps
    pattern = r"([\d.]+):[ \t]*(\(.*?\))[ \t]*\[(.*?)\]"

    # Compile the pattern for performance
    step_pattern = re.compile(pattern)

    # Parse the plan steps into PlanAction objects
    plan_steps = []
    for line in plan_text.split('\n'):
        # Ignore comments and empty lines
        if not line.strip() or line.strip().startswith(';'):
            continue
    
        # Match the pattern to extract time, action, and duration
        match = step_pattern.match(line)
        if match:
            time = float(match.group(1))
            action = match.group(2).strip().lower()
            op,args = parse_action_str(action)
            duration = float(match.group(3))
            # Create a PlanAction object and append it to the plan_steps list
            plan_action = planning_types.PlanAction(time, op, args, duration)
            plan_steps.append(plan_action)

    # Sort the plan steps by start time
    plan_steps.sort(key=lambda x: x.time)

    return plan_steps



