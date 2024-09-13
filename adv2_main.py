import numpy as np
import gpxpy
import gpxpy.gpx
from pykalman import KalmanFilter
from math import radians, sin, cos, sqrt, atan2


# Haversine formula to calculate distance between two GPS points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of Earth in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Load GPX data from a file
def load_gpx(filename):
    with open(filename, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    return gpx

# Save filtered data to a new GPX file
def save_gpx(gpx, filename):
    with open(filename, 'w') as f:
        f.write(gpx.to_xml())

# Apply Kalman Filter for smoothing
def apply_kalman_filter(gps_data):
    kf = KalmanFilter(initial_state_mean=gps_data[0],
                      n_dim_obs=2)  # GPS has two dimensions (lat, lon)
    smoothed_data, _ = kf.smooth(gps_data)
    return smoothed_data

# RDP Algorithm to simplify the track
def rdp(points, epsilon):
    def perpendicular_distance(pt, line_start, line_end):
        if np.array_equal(line_start, line_end):
            return np.linalg.norm(pt - line_start)
        else:
            return np.abs(np.cross(line_end-line_start, line_start-pt) / np.linalg.norm(line_end-line_start))

    if len(points) < 3:
        return points

    # Find the point with the maximum distance
    start, end = points[0], points[-1]
    dmax, index = max((perpendicular_distance(points[i], start, end), i) for i in range(1, len(points)-1))

    # If max distance is greater than epsilon, recursively simplify
    if dmax > epsilon:
        result1 = rdp(points[:index+1], epsilon)
        result2 = rdp(points[index:], epsilon)
        return np.vstack((result1[:-1], result2))
    else:
        return np.array([start, end])

# Compute total distance between the filtered points
def compute_total_distance(filtered_points):
    total_distance = 0
    for i in range(len(filtered_points) - 1):
        total_distance += haversine(filtered_points[i][0], filtered_points[i][1],
                                    filtered_points[i+1][0], filtered_points[i+1][1])
    return total_distance

# Main function to process GPX file
def process_gpx_file(input_gpx_file, output_gpx_file, epsilon=0.0001):
    # Load GPX
    gpx = load_gpx(input_gpx_file)
    gps_points = []

    # Extract GPS points from GPX file
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                gps_points.append([point.latitude, point.longitude])

    gps_points = np.array(gps_points)

    # Step 1: Smooth the points using Kalman Filter
    smoothed_points = apply_kalman_filter(gps_points)

    # Step 2: Simplify the points using RDP
    simplified_points = rdp(smoothed_points, epsilon)

    # Step 3: Create a new GPX file with filtered points
    new_gpx = gpxpy.gpx.GPX()
    new_track = gpxpy.gpx.GPXTrack()
    new_gpx.tracks.append(new_track)
    new_segment = gpxpy.gpx.GPXTrackSegment()
    new_track.segments.append(new_segment)

    for point in simplified_points:
        new_segment.points.append(gpxpy.gpx.GPXTrackPoint(point[0], point[1]))

    # Step 4: Compute the total distance
    total_distance = compute_total_distance(simplified_points)

    # Save filtered GPX
    save_gpx(new_gpx, output_gpx_file)

    print(f"Total distance: {total_distance:.2f} km")

# Example usage
filename = '22-00003879'
# filename = '5734459'
input_gpx_file = f'data/{filename}.gpx'
output_gpx_file = f'data/{filename}-snap-filtered.gpx'

process_gpx_file(input_gpx_file, output_gpx_file, epsilon=0.0005)
