#!/usr/bin/env python3
"""
Create simple test PLY files for demonstrating the segment_ply.py functionality.
"""

import numpy as np
import os
from sam2point.ply_utils import write_ply

def create_test_data():
    """Create simple test PLY files for demonstration."""
    
    # Create a simple cube point cloud
    n_points_per_side = 20
    coords = np.linspace(0, 10, n_points_per_side)
    
    # Generate points for a cube-like structure
    points = []
    colors = []
    
    # Add points throughout a 3D grid
    for x in coords:
        for y in coords:
            for z in coords:
                # Add some randomness to make it more interesting
                if np.random.random() > 0.7:  # Only keep 30% of points
                    points.append([x, y, z])
                    # Random colors
                    colors.append([
                        np.random.randint(100, 200),
                        np.random.randint(100, 200), 
                        np.random.randint(100, 200)
                    ])
    
    # Add a distinct object in the middle
    center_x, center_y, center_z = 5, 5, 5
    for i in range(100):
        # Create a sphere-like cluster
        theta = np.random.uniform(0, 2*np.pi)
        phi = np.random.uniform(0, np.pi)
        r = np.random.uniform(0.5, 1.5)
        
        x = center_x + r * np.sin(phi) * np.cos(theta)
        y = center_y + r * np.sin(phi) * np.sin(theta)
        z = center_z + r * np.cos(phi)
        
        points.append([x, y, z])
        # Make this object blue-ish
        colors.append([50, 100, 200])
    
    points = np.array(points)
    colors = np.array(colors)
    
    # Save the main point cloud
    os.makedirs('test_data', exist_ok=True)
    write_ply('test_data/test_scene.ply', points, colors)
    print(f"Created test scene with {len(points)} points: test_data/test_scene.ply")
    
    # Create prompt points (red points indicating what to segment)
    prompt_points = []
    prompt_colors = []
    
    # Add a few red points in the center object area
    for i in range(5):
        x = center_x + np.random.uniform(-0.5, 0.5)
        y = center_y + np.random.uniform(-0.5, 0.5) 
        z = center_z + np.random.uniform(-0.5, 0.5)
        
        prompt_points.append([x, y, z])
        prompt_colors.append([255, 0, 0])  # Red color
    
    # Add some non-red points to test filtering
    for i in range(10):
        x = np.random.uniform(0, 10)
        y = np.random.uniform(0, 10)
        z = np.random.uniform(0, 10)
        
        prompt_points.append([x, y, z])
        prompt_colors.append([0, 255, 0])  # Green color (should be ignored)
    
    prompt_points = np.array(prompt_points)
    prompt_colors = np.array(prompt_colors)
    
    write_ply('test_data/test_prompts.ply', prompt_points, prompt_colors)
    print(f"Created prompt file with {len(prompt_points)} points (5 red): test_data/test_prompts.ply")
    
    return 'test_data/test_scene.ply', 'test_data/test_prompts.ply'

if __name__ == '__main__':
    scene_file, prompts_file = create_test_data()
    print("\nTo test the segmentation, run:")
    print(f"python segment_ply.py --image {scene_file} --points {prompts_file} --output test_data/result.ply")