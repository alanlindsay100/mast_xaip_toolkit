import os
import requests
import json

from ..pddl_resources.parder import PddlDomainParser, PddlProblemParser, PDDLPlanParser
from ..pddl_resources.planning_types import Problem, State
from .state_reclaimer import read_state_lines
from .pddl_io import parse_raw_plan, write_out_plan, parse_plan
from ..util import FileUtil

import subprocess
import random

from . import optic_parser27 as optic_parser, optic_runner as OR

try:
  import tamer
except: pass

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

MONITOR_OPTIC=False


def read_applicable_actions():
  lines = list(filter(lambda x: not x == "", map(lambda x: x.strip(), open("applicable_actions").readlines())))
  app_actions = []; cas=[]
  for line in lines:
    if "@" in line:
      if len(cas)>0:
        app_actions.append(cas)
        cas = []
    else: 
      cas.append(line.split(" "))
  return app_actions



def appendSeed(seed) :
  seed_file.write(str(seed) + "\n")

def run_optic(domain_path, problem_path, time_limit=1800, memory_limit=8000000, code_ret=False):
  if MONITOR_OPTIC:
    return run_and_monitor_optic(domain_path, problem_path, time_limit, memory_limit, code_ret)
  planner_bits=["stdbuf", "-oL", OR.OPTIC_PLANNER_COMMAND]
  resource_f = OR.get_limit_curry(time_limit, memory_limit* 1024)
  args_plan = planner_bits+ [domain_path, problem_path]
  process = subprocess.Popen(args_plan, stdout=subprocess.PIPE, preexec_fn=resource_f)
  stdout, _ = process.communicate()
  return optic_parser.parse_optic(stdout,code_ret=code_ret)

def run_optic_client(domain_file_path, problem_file_path, time_limit=1800, memory_limit=4000000, code_ret=False):
    
    if MONITOR_OPTIC:
      url = "http://localhost:5000/monitored_optic_runner"
    else:
      url = "http://localhost:5000/run_optic"
    
    payload = {
        'domain_file': domain_file_path,
        'problem_file': problem_file_path,
        'time_limit': time_limit,
        'memory_limit': memory_limit
    }

    headers = {'Content-Type': 'application/json'}    
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(f"Status code {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"here is the result:\n{result['result']}")
        return optic_parser.parse_optic(result['result'],code_ret=code_ret)
    else:
        return {'error': response.text}

def run_and_monitor_optic(domain_path, problem_path, time_limit=1800, memory_limit=4000000, code_ret=False):
  return OR.run_optic(domain_path, problem_path, time_limit, memory_limit, code_ret)


def get_optic_instantiations(domain_path, problem_path, time_limit=1800, memory_limit=4000000):
  planner_bits=["stdbuf", "-oL", OR.OPTIC_PLANNER_COMMAND, "-@"]
  args_plan = planner_bits+ [domain_path, problem_path]
  resource_f = OR.get_limit_curry(time_limit, memory_limit* 1024)
  process = subprocess.Popen(args_plan, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=resource_f)
  stdout, _ = process.communicate()
  return optic_parser.parse_instantiated_actions(stdout)

def get_optic_instantiations_client(domain_file_path, problem_file_path, time_limit=1800, memory_limit=4000000):
    url = "http://localhost:5000/get_optic_instantiations"
    headers = {'Content-Type': 'application/json'}    
    payload = {
        'domain_file': domain_file_path,
        'problem_file': problem_file_path,
        'time_limit': time_limit,
        'memory_limit': memory_limit,
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()
        return optic_parser.parse_instantiated_actions(result['result'])
    else:
        return {'error': response.text}

def run_tamer(domain_path, problem_path):
  s = tamer.plan(domain_path, problem_path)
  if not s == None:
    return optic_parser.parse_tamer(s)



