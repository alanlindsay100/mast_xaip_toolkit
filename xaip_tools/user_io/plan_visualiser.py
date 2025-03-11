
import os, random, math

from . import best_match, template_plan_verbaliser as verbaliser
from .visualisation_extensions import survey_graph_ext as sm
from ..xaip_util import temp_fs_path


DEFAULT_POINT={"color":"black", "label":False}
DEFAULT_AREA={"color":"black", "label":False}

SCALE=1200
DIGRAPH=True
T=""
diffX=0
point2pos={}

script_dir = os.path.dirname(os.path.abspath(__file__))


def case_insensitive_lookup(d, kK):
  lkK = kK.lower()
  for k in d:
    if k.lower() == lkK:
      return d[k]

def make_node_str(origin, name, point, c, has_label, annotate=False):
  point2pos[name]=point
  if has_label:
    label = name
    shape = "ellipse"
  if not has_label:
    label = ""
    shape = "point"
  x=diffX+(SCALE* ( point[0] - origin[0]))
  node_info=""
  if annotate:
    node_info = ", title=\"[" + str(point[0]) + "," + str(point[1]) + "] " + str(name) + "\""
  return name.lower()+str(T) + " [label=\"" + label + "\",shape=\"" + shape +"\",style=\"filled\",fillcolor=\"white\",color=\"" + c +"\",pos=\"" + str(x) + "," +str(SCALE * (point[1] - origin[1])) +"!\"" + node_info +"]"

def make_label(P, a, c, annotate=False):
  polygon = list(map(lambda pn: pn.point, a.sub_labels))
  xs = list(map(lambda x: x[0], polygon))
  ax = (1.0*sum(xs)) / len(xs)
  ys = list(map(lambda x: x[1], polygon))
  ay = (1.0*sum(ys)) / len(ys)
  return make_node_str(P.origin, a.label, (ax, ay), c, True, annotate=annotate)

def make_area_str(P, a, c, label, annotate=False):
  _nds = a.sub_labels
  s=""
  if DIGRAPH:
    for p1, p2 in zip(_nds, _nds[1:] + [_nds[0]]):
      s += p1.o.lower()+str(T) + " -> " + p2.o.lower()+str(T) + " [weight=1000,style=dashed,penwidth=1,dir=none,color=\"" + str(c) + "\"]\n"
  else:
    for p1, p2 in zip(_nds, _nds[1:] + [_nds[0]]):
      s += p1.o.lower()+str(T) + " -- " + p2.o.lower()+str(T) + " [weight=1000,style=dashed,penwidth=1,dir=none,color=\"" + str(c) + "\"]\n"
  if label:
    s += make_label(P, a, c, annotate)
  return s


def get_point_rule(p, R):
  for r in R:
    if r["tag"] in p.tags:
      return r
  return DEFAULT_POINT

def get_area_rule(a, R):
  for r in R:
    if r["tag"] in a.tags:
      return r
  return DEFAULT_AREA

def make_dot_mission_structure(P, VI, edge_sym, annotate=False):
  s = ""
  for p in P.get_points():
    r = get_point_rule(p, VI.structure_rules)
    s += make_node_str(P.origin, p.o, p.point, r["color"], r["label"], annotate=annotate) + "\n"
  for a in P.get_areas():
    r = get_area_rule(a, VI.structure_rules)
    s += make_area_str(P, a, r["color"], r["label"], annotate=annotate) + "\n"
  return s

def get_max_dim(P, dim):
  return max(map(lambda x: SCALE*(x.point[dim]-P.origin[dim]), P.get_points()))
def get_min_dim(P, dim):
  return min(map(lambda x: SCALE*(x.point[dim]-P.origin[dim]), P.get_points()))

def get_assets(PI, R):
  assets = set()
  for pi in PI:
    for a in pi:
      if a.predicate in R:
        r = R[a.predicate]
        assets.add(a.arguments[r["color"]])
  return assets

def get_asset_steps(asset, pi, R):
  return list(filter(lambda a: a.arguments[R[a.predicate]["color"]]==asset, filter(lambda x: len(x.arguments)>0 and x.predicate in R, pi)))

def get_asset_plans(asset, PI, R):
  return list(map(lambda pi: get_asset_steps(asset, pi, R), PI))

def get_plan_sets(pi1, pi2, R, assets):
  ppairs = []
  if len(pi2) > 0:
    for asset in assets:
      ppairs.append(get_asset_plans(asset, [pi1,pi2], R))
  else:
    ppairs.append((pi1, pi2))
  return ppairs

def distance(p1,p2):
  return pow(pow(p1[0] - p2[0],2) + pow(p1[1] - p2[1], 2), 0.5)

def determine_direction(inn, outn, lmloc1, lmloc2, d):
  inp = case_insensitive_lookup(point2pos, inn)
  outp = case_insensitive_lookup(point2pos, outn)
  d1 = distance(inp, lmloc1) + distance(outp, lmloc2)
  d2 = distance(inp, lmloc2) + distance(outp, lmloc1)
  
  if d1 <= d2:
    return ((inn,d[lmloc1]),(outn, d[lmloc2]))
  return ((inn,d[lmloc2]),(outn, d[lmloc1]))

def make_structure_dot_str(P, VI, annotate=False, depth=0):
  if DIGRAPH:
    edge_sym = " -> "
    allow_repeats = True
    graph_designator = "digraph"
  else:
    edge_sym = " -- "
    allow_repeats = False
    graph_designator = "graph"
  graph_name = "D_" + str(depth)
    
  s = graph_designator + " " + graph_name + " {\n nodesep=0;\n splines = true;\n"  
  s += make_dot_mission_structure(P, VI, edge_sym, annotate=annotate)
  s += "}\n"
  return s

def make_dot_str(P, VI, ot, opi1, opi2, overlay=False, annotate=False, depth=0):
  global T, diffX
  if DIGRAPH:
    edge_sym = " -> "
    allow_repeats = True
    graph_designator = "digraph"
  else:
    edge_sym = " -- "
    allow_repeats = False
    graph_designator = "graph"
  graph_name = "D_" + str(depth)
  if len(opi2) > 0:
    graph_name += "_C_" + str(depth+1)
  
  max_t = max(map(lambda a: a.time+a.duration, opi1 + opi2))
  
  T=""; diffX=0
  s = graph_designator + " " + graph_name + " {\n nodesep=0;\n splines = true;\n"  
  s += "//--- Structure ---------------------------\n"
  s += make_dot_mission_structure(P, VI, edge_sym, annotate=annotate)
  s += "//--------------------------------------\n"
  
  if not overlay and len(opi2)>0:
    shift_x_t="_shifted"
    T=shift_x_t
    max_x=get_max_dim(P, 0)
    max_y=get_max_dim(P, 1)
    min_x=get_min_dim(P, 0)
    min_y=get_min_dim(P, 1)
    dx = max_x*0.02
    x = max_x + dx
    x_offset = max_x - min_x + 2*dx
    diffX = x_offset
    s += "//--- Offset structure ---------------------------\n"
    s += "a [shape=point, pos=\""+str(x)+","+str(min_y)+"!\", width=0.1, height=0.1];\n"
    s += "b [shape=point,pos=\""+str(x)+","+str(max_y)+"!\", width=0.1, height=0.1];\n"
    s += "a -> b [style=dashed, penwidth=5, color=\"grey\", dir=none];\n"
    s += make_dot_mission_structure(P, VI, edge_sym, annotate=annotate)  
    s += "//--------------------------------------\n"
    T=""; diffX=0
    offset_tups = [(0, ""),(x_offset, shift_x_t),(0, ""),(x_offset, shift_x_t)]
  else:
    offset_tups = [(None, ""),(0, ""),(0, ""),(0, "")]

  assets = list(get_assets((opi1, opi2), VI.plan_rules))
  for plan_pair in get_plan_sets(opi1, opi2, VI.plan_rules, assets):
    s += "  //--- Asset plan pair ---------------------------\n"
    pi1, pi2 = plan_pair
    
    covered1 = list()
    covered2 = list()
      
    v, iz = best_match.levenshtein_distance_with_indices(list(map(lambda a: [a.predicate] + a.arguments, pi1)), list(map(lambda a: [a.predicate] + a.arguments, pi2)))
    covered1 += list(map(lambda x: x[0], iz))
    covered2 += list(map(lambda x: x[1], iz))
      
    pi0c = list(map(lambda i: pi1[i], filter(lambda x: x in covered1, range(len(pi1)))))
    pi1c = list(map(lambda i: pi1[i], filter(lambda x: not x in covered1, range(len(pi1)))))
    pi2c = list(map(lambda i: pi2[i], filter(lambda x: not x in covered2, range(len(pi2)))))
    
    #if len(pi1)>0 and 1.0*len(pi0c)/len(pi1) > 0.5: # tags="old;new", tags="old", tags="new"
    if len(opi2) > 0:
      pi0, pi1, pi2 = (pi0c,["old","new"]), (pi1c,["old"]), (pi2c,["new"])
    else: 
      pi0, pi1, pi2 = (pi1,["active"]), (pi2,["active"]), ([],["active"])
    for (pi, tags), c, tsty, (dx, dxlabel) in zip((pi0, pi0, pi1, pi2), (["dodgerblue","midnightblue","cyan","darkviolet","darkorchid4"],["dodgerblue","midnightblue","cyan","darkviolet","darkorchid4"],["lightgreen","forestgreen","olivedrab3","darkgoldenrod1","palegreen4"],  ["tomato","maroon","orangered","chocolate","deeppink"]), ("solid","solid","solid","solid"), offset_tups):
      s += "    //--- Asset plan ---------------------------\n"
      if dx == None: continue
      diffX=dx
      T=dxlabel
      for pa in pi:
        a = [pa.predicate] + pa.arguments
        if len(a)==1: continue
        sty=tsty; pen = 4
        if a[0] in VI.plan_rules:
          r = VI.plan_rules[a[0]]
          asset = a[r["color"]+1]
          nfrom = a[r["start_p"]+1]+str(T)
          nto = a[r["end_p"]+1]+str(T)
          tc = c[assets.index(asset)%len(c)]
          head="normal"
          pen = ((1.0*pa.time + 0.5*pa.duration) / max_t) * 8
          label_str = ""
          action_info = make_action_info(pa, asset, tags, ot, annotate, depth)
          if "label" in r and not r["label"] == None:
            label_str = ",label=\"" + a[1+r["label"]]+"\""
          
          t = r["type"] 
          
          if t == "dotted" or t == "dashed":
            sty = t
            t = "line"

          if t == "line":
            head = "normal"
            s += nfrom + edge_sym + nto + " [arrowhead="+head+",color=\"" + tc+ "\",style=\"" + sty+ "\",weight=0,penwidth=" + str(pen)+ ",splines=true" + label_str + action_info+"]\n" 
          elif t == "odot":
            head = "odot"
            s += nfrom + edge_sym + nto + " [arrowhead="+head+",color=\"" + tc+ "\",style=\"" + sty+ "\",weight=0,penwidth=" + str(pen)+ ",splines=true" + label_str + action_info+"]\n" 
          elif t == "lawnmower":
            area = P[a[r["area_label"]+1]]
            polygon = list(map(lambda pn: pn.point, area.sub_labels))
            ps =sm.generate_connected_lawnmower_pattern(polygon, 6)
            points = set()
            for e in ps.geoms:
              p1,p2 =e.coords
              points.add(p1); points.add(p2)
            delta_x = diffX#0.5*random.random() - 0.25
            d = {}
            for p in points:
              name = area.label + "_lm"+str(len(d))
              d[p] = name
              s += name + T + " [label=\"\",shape=point,pos=\"" +str(delta_x + SCALE* (p[0] - P.origin[0])) + "," +str(SCALE* (p[1] - P.origin[1])) +"!\"]\n"
            for e in ps.geoms:
              p1,p2 =e.coords
              s += d[p1] + T + edge_sym + d[p2] + T+ " [dir=none,penwidth=" + str(pen)+ ",color=\"" + tc+ "\"" + action_info+"]\n"
            e1, e2 = determine_direction(a[2], a[3], ps.geoms[0].coords[0], ps.geoms[-1].coords[-1], d)
            s += e1[0] + T + edge_sym + e1[1] + T+ " [dir=none,penwidth=" + str(pen)+ ",color=\"" + tc+ "\"" + action_info+"]\n"
            s += e2[0] + T + edge_sym + e2[1] + T +" [dir=none,penwidth=" + str(pen)+ ",color=\"" + tc+ "\"" + action_info+"]\n"
      s += "    //--------------------------------------\n"
    s += "  //--------------------------------------\n"
  s += "//--------------------------------------\n"
  s += "}\n"
  return s

def make_action_info(a, asset, tags, ot, annotate, depth):
  if annotate:
    tag_str = ""
    if len(tags) > 0:
      tag_str = ", tags=\"" + ":".join(tags) + "\""
    return ",title=\"" + verbaliser.get_action_str(a, ot) + "\", asset=\"" + asset+ "\", plan_id=" + str(depth) + tag_str
  return ""

def get_appropriate_scaling_factor(points, max_width, max_height):
  x_coords = [p[0] for p in points]
  y_coords = [p[1] for p in points]
    
  current_min_x, current_max_x = min(x_coords), max(x_coords)
  current_min_y, current_max_y = min(y_coords), max(y_coords)
    
  current_width = current_max_x - current_min_x
  current_height = current_max_y - current_min_y
    
  width_scaling_factor = max_width / current_width
  height_scaling_factor = max_height / current_height
    
  return math.sqrt(len(points)) * min(width_scaling_factor, height_scaling_factor)

def set_graph_scale(P):
  global SCALE
  points = list(map(lambda p: p.point, P.get_points()))
    
  SCALE = get_appropriate_scaling_factor(points, 5, 6)
  print ("*** SCALE CHANGED TO ", SCALE)
  return SCALE

def create_dot(P, VI, ot, PI, depth=0):
  fns = list()
  fn = temp_fs_path + "/_asset_dot_"+str(len(PI))+".dot"
  if len(PI) == 1:
    PI = [PI[0],[]]
  s = make_dot_str(P, VI, ot, PI[0],PI[1], overlay=VI.overlay, annotate=True, depth=depth)
  open(fn, 'w').write(s)
  fns.append(fn)
  return fns
def create_structure_dot(P, VI):
  fn = temp_fs_path + "/_structure_dot.dot"
  s = make_structure_dot_str(P, VI, annotate=True)
  open(fn, 'w').write(s)
  return fn
