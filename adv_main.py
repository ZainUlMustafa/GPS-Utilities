import openrouteservice
import gpxpy
import gpxpy.gpx
import math
from geopy.distance import geodesic
from datetime import datetime

ORS_API_KEY = '5b3ce3597851110001cf624834d47bd5d59747d8bb2e4f065df3d60d'
client = openrouteservice.Client(key=ORS_API_KEY)

# Parse GPX file with timestamp information
def parse_gpx(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'time': point.time
                })
    return points

# Sample points with a fixed interval
def sample_gpx_points(points, num_samples=10):
    interval = max(1, len(points) // num_samples)
    sampled_points = points[::interval]
    sampled_points.append(points[-1])  # Ensure last point is included
    return sampled_points

# Snap points to road using OpenRouteService
def snap_to_road(points):
    coordinates = [(point['longitude'], point['latitude']) for point in points]
    snapped_coords = []
    try:
        routes = client.directions(coordinates, profile='driving-car', format='geojson')
        for step in routes['features'][0]['geometry']['coordinates']:
            snapped_coords.append({
                'latitude': step[1],
                'longitude': step[0],
                'time': None  # Time is lost during snapping
            })
    except Exception as e:
        print(f"Error snapping to road: {e}")
    return snapped_coords

# Calculate distance between points
def calculate_distance(coords):
    total_distance = 0.0
    for i in range(1, len(coords)):
        total_distance += geodesic(
            (coords[i-1]['latitude'], coords[i-1]['longitude']),
            (coords[i]['latitude'], coords[i]['longitude'])
        ).km
    return total_distance

# Detect U-turns by calculating angle between points
def calculate_angle(p1, p2, p3):
    def calculate_bearing(point1, point2):
        lat1, lon1 = math.radians(point1['latitude']), math.radians(point1['longitude'])
        lat2, lon2 = math.radians(point2['latitude']), math.radians(point2['longitude'])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    bearing1 = calculate_bearing(p1, p2)
    bearing2 = calculate_bearing(p2, p3)
    
    angle = abs(bearing2 - bearing1)
    if angle > 180:
        angle = 360 - angle
    return angle

# Filter points based on sharp angle changes (possible U-turns)
def filter_u_turns(points, angle_threshold=135):
    filtered_points = [points[0]]  # Start with the first point
    for i in range(1, len(points) - 1):
        angle = calculate_angle(points[i-1], points[i], points[i+1])
        if angle < angle_threshold:
            filtered_points.append(points[i])
    filtered_points.append(points[-1])  # Include last point
    return filtered_points

# Filter points based on abnormal speed changes
def filter_abnormal_speed(points, speed_threshold=50):  # Threshold in km/h
    filtered_points = [points[0]]  # Keep the first point
    for i in range(1, len(points)):
        time_diff = (points[i]['time'] - points[i-1]['time']).total_seconds() / 3600.0  # Time in hours
        distance = geodesic((points[i-1]['latitude'], points[i-1]['longitude']),
                            (points[i]['latitude'], points[i]['longitude'])).km
        if time_diff > 0:  # Avoid division by zero
            speed = distance / time_diff
            print(speed)
            if speed < speed_threshold:
                filtered_points.append(points[i])
    return filtered_points

# Write the snapped coordinates back into a GPX file
def write_gpx(snapped_coords, output_file):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for point in snapped_coords:
        segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=point['latitude'], longitude=point['longitude']))

    with open(output_file, 'w') as f:
        f.write(gpx.to_xml())

# Main function to process GPX with filtering for U-turns and speed changes
def process_gpx_with_filters(input_file, output_file, num_samples=10, angle_threshold=135, speed_threshold=50):
    points = parse_gpx(input_file)
    sampled_points = sample_gpx_points(points, num_samples)
    
    # Filter for U-turns and abnormal speed changes
    filtered_points = filter_u_turns(sampled_points, angle_threshold)
    filtered_points = filter_abnormal_speed(filtered_points, speed_threshold)
    
    snapped_coords = snap_to_road(filtered_points)
    if snapped_coords:
        total_distance = calculate_distance(snapped_coords)
        write_gpx(snapped_coords, output_file)
        print(f"Total snapped distance: {total_distance:.2f} km")
    else:
        print("No snapped coordinates returned.")

# Example usage
filename = '22-00003897'
# filename = '5734459'
input_gpx_file = f'data/{filename}.gpx'
output_gpx_file = f'data/{filename}-snap-filtered.gpx'

process_gpx_with_filters(input_gpx_file, output_gpx_file, 50)
