import yaml

from . import mast







class ScenarioPoints:
  def __init__(self):
    self.located_entity_map = {}
  def __getitem__(self, key):
    return self.located_entity_map[key]
  def __setitem__(self, key, value):
    self.located_entity_map[key] = value
  def __delitem__(self, key):
    del self.located_entity_map[key]
  def __contains__(self, key):
    return key in self.located_entity_map
  def keys(self):
    return self.located_entity_map.keys()
  def get_points(self):
    return list(filter(lambda v: isinstance(v, mast.location_point), self.located_entity_map.values()))
  def get_areas(self):
    return list(filter(lambda v: isinstance(v, mast.location_label) and v.is_area, self.located_entity_map.values()))
  def get_collections(self):
    return list(filter(lambda v: isinstance(v, mast.location_label) and not v.is_area, self.located_entity_map.values()))
  
  

# XXX we have ignored non-modelled points - like transponders.
def parse_points(l, P):
  for e in l:
    label = e["label"]
    lp = mast.location_point(label, e["point"], True)
    if "tags" in e:
      lp.tags = e["tags"]
    else: 
      lp.tags = list()
    P[label] = lp
def parse_areas(l, P):
  for e in l:
    label = e["label"]
    lp = mast.location_label(label, list(map(lambda x: P[x], e["polygon"]))	, True)
    #lp = mast.location_label(label, e["polygon"]	, True)
    if "tags" in e:
      lp.tags = e["tags"]
    else: 
      lp.tags = list()
    P[label] = lp
def parse_collections(l, P):
  for e in l:
    label = e["label"]
    lp = mast.location_label(label, list(map(lambda x: P[x], e["elements"])), False)
    #lp = mast.location_label(label, e["elements"], False)
    if "tags" in e:
      lp.tags = e["tags"]
    else: 
      lp.tags = list()
    P[label] = lp
def parse_properties(d, P):
  P.near = d["near"]
  P.origin = d["origin"]
  P.scale = d["scale"]

def load_points(po_fn):
  f = open(po_fn, 'r')
  data = yaml.safe_load(f)
  P = ScenarioPoints()
  parse_points(data["Points"], P)
  parse_areas(data["Areas"], P)
  parse_collections(data["Collections"], P)
  parse_properties(data["SpatialProperties"], P)
  return P
  
