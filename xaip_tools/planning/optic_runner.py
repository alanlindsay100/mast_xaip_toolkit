
import subprocess
import os
import threading, select
import time
import resource

from . import optic_parser27 as optic_parser


script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

OPTIC_PLANNER_COMMAND=""

def set_nonblocking(fd):
    import fcntl
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def non_blocking_read(proc, the_buffer, stop_event):  
  fd = proc.stdout.fileno()
  while not stop_event.is_set():
    rlist, _, _ = select.select([proc.stdout], [], [], 0.1)
    
    if rlist:
      chunk = os.read(fd, 1024)  # Read in small chunks
      if chunk:
        the_buffer.add(chunk)
        #print(buffer.decode(errors='replace'), end='')  # Process data chunk as it comes
      else:
        break  # Process has finished and no more data

class buffer:
  def __init__(self):
    self.buffer = b''
  def add(self, chunk):
    self.buffer += chunk
    
def condition(line):
    return "; Plan found with metric" in line
    #return "* All goal deadlines now no later than" in line    
    
def monitor_process(proc, condition):
    stop_event = threading.Event()
    the_buffer=buffer()
    t = threading.Thread(target=non_blocking_read, args=(proc, the_buffer, stop_event))
    t.start()
    while proc.poll() is None:
        if condition(the_buffer.buffer.decode(errors='replace')):
            time.sleep(1)
            try:
                proc.kill()
            except:
                pass
            time.sleep(0.1)
            stop_event.set()
            time.sleep(0.1)
            break
        time.sleep(1)
    t.join()
    return the_buffer.buffer.decode(errors='replace')

def get_limit_curry(time_limit, memory_limit) : 
  def set_limits():
    # Set virtual memory limit to X
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    # Set CPU time limit to Y seconds
    resource.setrlimit(resource.RLIMIT_CPU, (time_limit, time_limit))
  return set_limits

    
def _run_and_monitor_optic(domain_path, problem_path, time_limit, memory_limit):
    planner_bits=["stdbuf", "-oL", OPTIC_PLANNER_COMMAND]
    args_plan = planner_bits+ [domain_path, problem_path]
    resource_f = get_limit_curry(time_limit, memory_limit* 1024)
    proc = subprocess.Popen(args_plan, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=resource_f )
    set_nonblocking(proc.stdout.fileno())
    return monitor_process(proc, condition)
    
def run_optic(domain_path, problem_path, time_limit=1800, memory_limit=4000000, code_ret=False):
    sb = _run_and_monitor_optic(domain_path, problem_path, time_limit, memory_limit)
    return optic_parser.parse_optic(sb,code_ret=code_ret)
def run_optic_client(domain_path, problem_path, time_limit=1800, memory_limit=4000000):
    global parent_dir
    parent_dir = "/opt/optic"
    sb = _run_and_monitor_optic(domain_path, problem_path, time_limit, memory_limit)
    return sb
def relay_optic_ouput(domain_path, problem_path, time_limit, memory_limit):    
    sb = _run_and_monitor_optic(domain_path, problem_path, time_limit, memory_limit)
    print (sb)
    
    
