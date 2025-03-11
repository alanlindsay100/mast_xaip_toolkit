import yaml

from . import mast


class VisualInterpretation:
  def __init__(self):
    self.plan_rules = None
    self.structure_rules = None
class SpatialInterpretation:
  def __init__(self):
    pass
class ResourceInterpretation:
  def __init__(self):
    pass


class DomainInterpretations:
  def __init__(self):
    self.visualisation = None
    self.spatial = None
    self.resource = None
    self.nl = None
    self.abstraction = None


def parse_visual_interpretation(d, DI):
  VI = VisualInterpretation()
  VI.plan_rules = dict(map(lambda e: (e["op"], e), d["plan_rules"]))
  VI.structure_rules = d["structure_rules"]
  VI.overlay = d["overlay"]
  DI.visualisation = VI

def parse_spatial_interpretation(d, DI):
  DI.spatial = d

def parse_resource_interpretation(l, DI):
  DI.resource = l

def parse_nl_interpretation(d, DI):
  DI.nl = d

def parse_abs_interpretation(d, DI):
  DI.abstraction = d

def load_interpretations(di_fn):
  DI = DomainInterpretations()
  f = open(di_fn, 'r')
  data = yaml.safe_load(f)["Interpretations"]
  
  parse_visual_interpretation(data["Visualisation"], DI)
  parse_nl_interpretation(data["NL"], DI)
  parse_spatial_interpretation(data["Spatial"], DI)
  parse_resource_interpretation(data["Resource"], DI)
  parse_abs_interpretation(data["Abstraction"], DI)

  return DI
