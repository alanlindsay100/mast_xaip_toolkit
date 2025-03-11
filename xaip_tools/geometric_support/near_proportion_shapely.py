
from shapely.geometry import LineString, Point, box
import time
import gc


LINES=dict()
RESULT=dict()
CIRCLE_MAP=dict()
ti=0
ts=0 
c=0

def get_time():
  try:
    t=time.perf_counter()
  except:
    t=time.time()
  return t

def percentage_within_circle(x1, y1, x2, y2, circle):
    # Define the line segment and the circle
    
    line =  LineString([(x1, y1), (x2, y2)])

    # Find the intersection between the line segment and the circle
    if line.intersects(circle):
      intersection = line.intersection(circle)
      # Calculate the length within the circle
      length_within_circle = intersection.length if not intersection.is_empty else 0

      # Calculate the total length of the line segment
      total_length = line.length
      del line, intersection
      # Calculate the percentage
      percentage = (length_within_circle / total_length) if total_length != 0 else 0
      return percentage
    return 0

def determine_percentage_within_radius_of_source(seg, circle):
  ((x1,y1),(x2,y2)) = seg
  return percentage_within_circle(x1, y1, x2, y2, circle)


def process_nodes(source, points, radius):
  circle = Point(source[0],source[1]).buffer(radius)
  l = []
  for (x,y) in points:
    if Point(x, y).within(circle):
      v = 1.0
    else:
      v = 0.0
    l.append(v)
  return l

def process_line_segments(source, segments, radius):
  global CIRCLE_MAP
  vs = []
  x3, y3 = source
  circle = Point(x3, y3).buffer(radius, resolution=16)
  for seg in segments:
    ((x1,y1),(x2,y2)) = seg
    if (x1,y1,x2,y2,x3,y3,radius) in RESULT:
      v = RESULT[(x1,y1,x2,y2,x3,y3,radius)]
    else:
      v = determine_percentage_within_radius_of_source(seg, circle)
      RESULT[(x1,y1,x2,y2,x3,y3,radius)] = v
    vs.append(v)   
      
  del circle
  return vs


