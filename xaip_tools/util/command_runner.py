import subprocess


def execute(args):
  process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, x = process.communicate()
  return stdout

