import numpy as np
import os


def read_ply(file_path):
    """
    Read a PLY file and return points and colors.
    
    Args:
        file_path (str): Path to the PLY file
        
    Returns:
        tuple: (points, colors) where points is Nx3 and colors is Nx3 (RGB values 0-255)
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Parse header
    header_end = 0
    vertex_count = 0
    properties = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('element vertex'):
            vertex_count = int(line.split()[-1])
        elif line.startswith('property'):
            properties.append(line.split()[-1])
        elif line == 'end_header':
            header_end = i + 1
            break
    
    if vertex_count == 0:
        raise ValueError("No vertices found in PLY file")
    
    # Read vertex data
    data_lines = lines[header_end:header_end + vertex_count]
    vertex_data = []
    
    for line in data_lines:
        values = line.strip().split()
        vertex_data.append([float(v) for v in values])
    
    vertex_data = np.array(vertex_data)
    
    # Extract coordinates (assuming first 3 columns are x, y, z)
    points = vertex_data[:, :3]
    
    # Extract colors if available
    colors = None
    if vertex_data.shape[1] >= 6:  # Assuming RGB are after x,y,z
        # Check if we have red, green, blue properties
        color_indices = []
        for prop in ['red', 'green', 'blue']:
            if prop in properties:
                color_indices.append(properties.index(prop))
        
        if len(color_indices) == 3:
            colors = vertex_data[:, color_indices]  # Use indices directly
        else:
            # Fallback: assume columns 3,4,5 are RGB
            colors = vertex_data[:, 3:6]
    
    if colors is None:
        # Default to white if no colors
        colors = np.ones((points.shape[0], 3)) * 255
    
    return points, colors


def write_ply(file_path, points, colors=None, mask=None, segmented_color=None):
    """
    Write points and colors to a PLY file.
    
    Args:
        file_path (str): Output PLY file path
        points (np.ndarray): Nx3 array of point coordinates
        colors (np.ndarray): Nx3 array of RGB colors (0-255)
        mask (np.ndarray): Boolean mask for segmentation visualization
        segmented_color (list or np.ndarray): RGB color for segmented points (default: [255, 0, 0] red)
    """
    if colors is None:
        colors = np.ones((points.shape[0], 3)) * 255
    
    # Apply mask coloring if provided
    if mask is not None:
        mask = mask.astype(bool)
        # Set segmented points to specified color (default red)
        if segmented_color is None:
            segmented_color = [255, 0, 0]  # Red by default
        colors = colors.copy()
        colors[mask] = segmented_color
    
    # Ensure colors are integers
    colors = colors.astype(np.uint8)
    
    with open(file_path, 'w') as f:
        # Write header
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        
        # Write vertex data
        for i in range(len(points)):
            f.write(f"{points[i, 0]:.6f} {points[i, 1]:.6f} {points[i, 2]:.6f} "
                   f"{colors[i, 0]} {colors[i, 1]} {colors[i, 2]}\n")


def extract_red_points(points, colors, tolerance=50):
    """
    Extract points that are marked as red (positive prompts).
    
    Args:
        points (np.ndarray): Nx3 array of point coordinates
        colors (np.ndarray): Nx3 array of RGB colors (0-255)
        tolerance (int): Tolerance for red color detection
        
    Returns:
        np.ndarray: Mx3 array of red points coordinates
    """
    # Find points that are predominantly red
    # Red should be high (close to 255), green and blue should be low
    red_mask = (colors[:, 0] > 255 - tolerance) & \
               (colors[:, 1] < tolerance) & \
               (colors[:, 2] < tolerance)
    
    red_points = points[red_mask]
    return red_points


def extract_green_points(points, colors, tolerance=50):
    """
    Extract points that are marked as green (negative prompts).
    
    Args:
        points (np.ndarray): Nx3 array of point coordinates
        colors (np.ndarray): Nx3 array of RGB colors (0-255)
        tolerance (int): Tolerance for green color detection
        
    Returns:
        np.ndarray: Mx3 array of green points coordinates
    """
    # Find points that are predominantly green
    # Green should be high (close to 255), red and blue should be low
    green_mask = (colors[:, 1] > 255 - tolerance) & \
                 (colors[:, 0] < tolerance) & \
                 (colors[:, 2] < tolerance)
    
    green_points = points[green_mask]
    return green_points


def load_ply_sample(data_path):
    """
    Load PLY sample in the format expected by SAM2Point.
    
    Args:
        data_path (str): Path to PLY file
        
    Returns:
        tuple: (point, color) normalized point cloud data
    """
    print("Loading point cloud from ", data_path)
    
    point, color = read_ply(data_path)
    
    # Normalize points to [0, 1]
    pmin = point.min(axis=0)
    point = point - pmin
    pmax = point.max(axis=0)
    point = point / pmax
    
    # Normalize colors to [0, 1]
    color = color / 255.0
    
    return point, color