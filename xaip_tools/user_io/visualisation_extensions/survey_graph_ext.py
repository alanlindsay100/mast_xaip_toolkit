import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, box, GeometryCollection
import matplotlib.pyplot as plt

def generate_connected_lawnmower_pattern(polygon_points, x_passes):
    polygon = Polygon(polygon_points)
    minx, miny, maxx, maxy = polygon.bounds

    # Determine the width of each pass
    pass_width = (maxx - minx) / x_passes

    # Generate the connected lawnmower pattern
    path = []
    for i in range(x_passes + 1):
        x = minx + i * pass_width
        if i % 2 == 0:
            # Go up
            path.append((x, miny))
            path.append((x, maxy))
        else:
            # Go down
            path.append((x, maxy))
            path.append((x, miny))
    
    # Create the connected path
    connected_path = LineString(path)

    # Intersect the connected path with the bounding box to clip it to the region
    bounding_box = box(minx, miny, maxx, maxy)
    clipped_path = connected_path.intersection(bounding_box)

    return clipped_path

def extract_coordinates(geometry):
    if isinstance(geometry, LineString):
        return [geometry.xy]
    elif isinstance(geometry, MultiLineString):
        coords = []
        for geom in geometry.geoms:
            coords.extend(extract_coordinates(geom))
        return coords
    elif isinstance(geometry, GeometryCollection):
        coords = []
        for geom in geometry.geoms:
            coords.extend(extract_coordinates(geom))
        return coords
    else:
        raise ValueError("Unsupported geometry type")

# Example usage
#polygon_points = [(1, 1), (5, 1), (6, 4), (4, 6), (1, 5)]
#x_passes = 4
#lawnmower_pattern = generate_connected_lawnmower_pattern(polygon_points, x_passes)

# Display the results
def plot_polygon_and_pattern(polygon_points, pattern_line):
    polygon = Polygon(polygon_points)
    x, y = polygon.exterior.xy
    plt.plot(x, y, label="Polygon")

    pattern_coords = extract_coordinates(pattern_line)
    for coords in pattern_coords:
        x, y = coords
        plt.plot(x, y, label="Lawnmower Path")

    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Lawnmower Pattern')
    plt.legend()
    plt.show()

#plot_polygon_and_pattern(polygon_points, lawnmower_pattern)

