
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union


def grow_poly_shape_abs(shape, growth_amount):
  polygon = Polygon(list(map(lambda p: p[:2], shape)))
  return polygon.buffer(growth_amount)

def grow_point_abs(shape, radius):
  print (shape, radius)
  return Point(shape[0],shape[1]).buffer(radius)
  
def grow_shapes(shapes, growth_amount = 10):
  grown_shapes = []
  for shape in shapes:
    if len(shape) == 1:
      grown_shapes.append(grow_point_abs(shape[0], growth_amount))
    else:
      grown_shapes.append(grow_poly_shape_abs(shape, growth_amount))
  return grown_shapes



def identify_proportion_of_edge_within_shapes(line, buffers):  
  combined_buffer = unary_union(buffers)
  intersection = line.intersection(combined_buffer)
  if not intersection.is_empty:
    intersected_length = intersection.length
    total_length = line.length
    proportion_within_buffer = intersected_length / total_length
  else:
    proportion_within_buffer = 0.0 
  return proportion_within_buffer

def identify_proportion_of_edges_within_shapes(lines, shapes):
  proportions = list()
  for (p1,p2) in lines:
    proportions.append(identify_proportion_of_edge_within_shapes(LineString([p1,p2]), shapes))
  return proportions


def is_point_in_any_buffer(buffers, point):
  return any(buffer.contains(point) for buffer in buffers)

def identify_points_within_shapes(points, shapes):
  return list(map(lambda p: is_point_in_any_buffer(shapes, Point(p[0], p[1])), points))



