#!/usr/bin/env python3
"""
Debug script to check prompt points in PLY file
"""

import sys
sys.path.append('.')

from sam2point.ply_utils import read_ply, extract_red_points
import numpy as np

def debug_prompt_file(points_file):
    print(f"Debugging prompt file: {points_file}")
    
    # Read the file
    points, colors = read_ply(points_file)
    print(f"Total points: {len(points)}")
    print(f"Points shape: {points.shape}")
    print(f"Colors shape: {colors.shape}")
    
    # Check color range
    print(f"Color range: min={colors.min(axis=0)}, max={colors.max(axis=0)}")
    
    # Extract red points with debug info
    tolerances = [0, 10, 30, 50, 100]
    
    for tol in tolerances:
        red_mask = (colors[:, 0] > 255 - tol) & \
                   (colors[:, 1] < tol) & \
                   (colors[:, 2] < tol)
        red_points = points[red_mask]
        print(f"With tolerance {tol}: found {len(red_points)} red points")
        
        if len(red_points) > 0:
            print(f"  Red points: {red_points}")
            print(f"  Red colors: {colors[red_mask]}")
    
    # Show first few points and colors
    print(f"\nFirst 10 points and colors:")
    for i in range(min(10, len(points))):
        print(f"  Point {i}: {points[i]} -> Color: {colors[i]}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python debug_prompts.py <prompt_file.ply>")
        sys.exit(1)
    
    debug_prompt_file(sys.argv[1])