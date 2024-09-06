import gpxpy
import geopy.distance

def load_gpx(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    return gpx
#enddef

def calculate_distance(point1, point2):
    coords_1 = (point1.latitude, point1.longitude)
    coords_2 = (point2.latitude, point2.longitude)
    return geopy.distance.distance(coords_1, coords_2).meters
#enddef

def filter_jitter(points, distance_threshold):
    filtered_points = [points[0]]
    for point in points[1:]:
        last_point = filtered_points[-1]
        if calculate_distance(last_point, point) > distance_threshold:
            filtered_points.append(point)
        #endif
    #endfor
    return filtered_points
#enddef

def total_distance(points):
    total_dist = 0
    for i in range(1, len(points)):
        total_dist += calculate_distance(points[i-1], points[i])
    #endfor
    return total_dist
#enddef

def export_filtered_gpx(filtered_points, output_file_path):
    new_gpx = gpxpy.gpx.GPX()
    
    gpx_track = gpxpy.gpx.GPXTrack()
    new_gpx.tracks.append(gpx_track)
    
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    for point in filtered_points:
        gpx_point = gpxpy.gpx.GPXTrackPoint(point.latitude, point.longitude, elevation=point.elevation, time=point.time)
        gpx_segment.points.append(gpx_point)
    #endfor
    
    with open(output_file_path, 'w') as f:
        f.write(new_gpx.to_xml())
    #endwith

    print(f"Filtered GPX exported to {output_file_path}")
#enddef

def process_gpx(file_path, output_file_path, distance_threshold=5):
    gpx = load_gpx(file_path)
    
    all_points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                all_points.append(point)
            #endfor
        #endfor
    #endfor
    
    filtered_points = filter_jitter(all_points, distance_threshold)
    
    dist = total_distance(filtered_points)
    print(f'Total distance after filtering: {dist:.2f} meters')
    
    export_filtered_gpx(filtered_points, output_file_path)
#enddef

gpx_file_path = 'data/5734459.gpx'
output_file_path = 'data/5734459-filtered_output.gpx'

process_gpx(gpx_file_path, output_file_path, distance_threshold=300)
