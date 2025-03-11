
def readlines(fname, comment="#") :
  f = open(fname)
  lines = []
  for l in f.readlines() :
    e = l.replace("\r\n","").replace("\n","")
    if e == None or e == "" : continue
    e = e.split(comment)[0]
    if not(e == None) and not (e == "") :
      lines.append(e)
  f.close()
  return lines

def readInKeyEntryPair(d, line) :
  import ast
  p = line.find("=")
  n = line[:p]
  dl = line[p+1:]
  de = ast.literal_eval(dl)
  d[n] = de


def readLines(fname) :
  f = open(fname)
  lines = f.readlines()
  f.close()
  return lines

def write(fn, s):
  f = open(fn, 'w')
  f.write(s)
  f.close()