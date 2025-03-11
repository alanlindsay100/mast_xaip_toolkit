import sys, re

"""
Due to the way Driverlog problems are generated there are certain assumptions that can be made about the form of these files.
These include that the link graph is connected, and with regards to line form and content.
"""

lines = list(map(lambda x: x.strip(), open(sys.argv[1]).readlines()))

nodes = []
edges = []

ttd = r"\(\=\s*\(time-to-drive\s+(\S+)\s+(\S+)\)\s+(\d+)\)"
ttw = r"\(\=\s*\(time-to-walk\s+(\S+)\s+(\S+)\)\s+(\d+)\)"

w = []
for line in lines:
  if "(link" in line or "(path" in line:
    e = line[len("(link "):-1].split(" ")
    for n in e:
      if not n in nodes:
        nodes.append(n)
    if not e in edges:
      edges.append(e)
  match_ttd = re.search(ttd, line)
  match_ttw = re.search(ttw, line)
  if match_ttd:
    from_loc, to_loc, time = match_ttd.groups()
    w.append((from_loc, to_loc, float(time)))
  if match_ttw:
    from_loc, to_loc, time = match_ttw.groups()
    w.append((from_loc, to_loc, float(time)/10.0))
    
def make_graph(w):
  s = "digraph {\n"
  for (n1,n2, t) in w:
    s += "  " + n1.replace("-","_") + " -> " + n2.replace("-","_") + " [len=" + str(t)+"]\n"
  s += "}\n"
  return s


print (make_graph(w))

