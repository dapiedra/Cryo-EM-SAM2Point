#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLY Segmentation Script for SAM2Point

This script provides 3D point cloud segmentation functionality for PLY files.
It reads a PLY point cloud file and a PLY file with red-colored prompt points,
then performs segmentation and outputs the result as a PLY file.

Usage:
    python segment_ply.py --image image.ply --points points.ply --output out.ply

The prompt points should be marked in red color (255, 0, 0) in the points PLY file.
"""

import os
import torch
import argparse
import numpy as np

from segment import seg_point
from sam2point.ply_utils import load_ply_sample, read_ply, write_ply, extract_red_points
from sam2point.voxelizer import Voxelizer
from sam2point.utils import cal

# Enable mixed precision for better performance
torch.autocast(device_type="cuda", dtype=torch.bfloat16).__enter__()

if torch.cuda.get_device_properties(0).major >= 8:
    # Turn on tfloat32 for Ampere GPUs
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


class Args:
    """Configuration class to mimic argparse args for compatibility with existing code."""
    def __init__(self, voxel_size=0.02, theta=0.5, mode='nearest', prompt_idx=0):
        self.voxel_size = voxel_size
        self.theta = theta
        self.mode = mode
        self.prompt_idx = prompt_idx
        self.dataset = 'PLY'
        self.sample_idx = 0
        self.prompt_type = 'point'


def segment_ply_pointcloud(image_path, points_path, output_path, voxel_size=0.02):
    """
    Segment a PLY point cloud using red-colored prompt points from another PLY file.
    
    Args:
        image_path (str): Path to the input PLY point cloud to segment
        points_path (str): Path to the PLY file containing red prompt points
        output_path (str): Path to save the segmented PLY file
        voxel_size (float): Voxel size for processing
    """
    print(f"Segmenting PLY point cloud...")
    print(f"Input image: {image_path}")
    print(f"Prompt points: {points_path}")
    print(f"Output: {output_path}")
    print(f"Voxel size: {voxel_size}")
    
    # Load the main point cloud to segment
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image file not found: {image_path}")
    
    point, color = load_ply_sample(image_path)
    print(f"Loaded {len(point)} points from image file")
    
    # Load prompt points
    if not os.path.exists(points_path):
        raise FileNotFoundError(f"Prompt points file not found: {points_path}")
    
    prompt_points_raw, prompt_colors_raw = read_ply(points_path)
    red_points = extract_red_points(prompt_points_raw, prompt_colors_raw)
    
    if len(red_points) == 0:
        raise ValueError("No red points found in the prompt points file. "
                        "Please mark prompt points with red color (255, 0, 0).")
    
    print(f"Found {len(red_points)} red prompt points")
    print(f"Red points (raw): {red_points}")
    
    # Load the main point cloud to get the same normalization
    main_points_raw, _ = read_ply(image_path)
    
    # Normalize prompt points to match the main point cloud coordinate system
    # Use the SAME transformation as applied to the main point cloud
    main_min = main_points_raw.min(axis=0)
    main_max = main_points_raw.max(axis=0)
    
    # Normalize red points using the same transformation
    red_points_normalized = (red_points - main_min) / (main_max - main_min)
    
    print(f"Main point cloud bounds: min={main_min}, max={main_max}")
    print(f"Red points (normalized): {red_points_normalized}")
    
    # Validate that normalized points are in valid range
    for i, pt in enumerate(red_points_normalized):
        if not (0 <= pt[0] <= 1 and 0 <= pt[1] <= 1 and 0 <= pt[2] <= 1):
            print(f"Warning: Prompt point {i} is outside [0,1] bounds: {pt}")
    
    # Create configuration
    args = Args(voxel_size=voxel_size)
    
    # Prepare data for voxelization
    point_color = np.concatenate([point, color], axis=1)
    voxelizer = Voxelizer(voxel_size=args.voxel_size, clip_bound=None)
    
    labels_in = point[:, :1].astype(int)
    locs, feats, labels, inds_reconstruct = voxelizer.voxelize(point, color, labels_in)
    
    print(f"Voxelized to {len(locs)} voxels")
    print(f"Voxel grid bounds: {locs.min(axis=0)} to {locs.max(axis=0)}")
    
    # Validate that prompt points will be within voxel bounds
    max_voxel_coords = locs.max(axis=0)
    prompt_list = red_points_normalized.tolist()
    
    # Filter out prompt points that would be outside voxel bounds
    valid_prompts = []
    for i, prompt_point in enumerate(prompt_list):
        # Convert to voxel coordinates to check bounds
        voxel_coord = np.array(prompt_point) / args.voxel_size + 2
        if all(0 <= coord < max_voxel_coords[j] + 5 for j, coord in enumerate(voxel_coord)):
            valid_prompts.append(prompt_point)
            print(f"Prompt {i+1} is valid: {prompt_point} -> voxel {voxel_coord}")
        else:
            print(f"Warning: Skipping prompt {i+1} outside voxel bounds: {prompt_point} -> voxel {voxel_coord}")
    
    if not valid_prompts:
        raise ValueError("No valid prompt points within voxel bounds")
    
    prompt_list = valid_prompts
    args.prompt_idx = 0  # Use first prompt point for main processing
    
    try:
        # Process each prompt point individually to avoid indexing issues
        all_masks = []
        for i, prompt_point in enumerate(prompt_list):
            print(f"Processing prompt point {i+1}/{len(prompt_list)}: {prompt_point}")
            args.prompt_idx = 0  # Always use index 0 since we pass one prompt at a time
            
            try:
                # Pass only one prompt point at a time
                single_prompt_list = [prompt_point]
                mask = seg_point(locs, feats, single_prompt_list, args)
                all_masks.append(mask)
                print(f"Successfully processed prompt point {i+1}")
            except Exception as e:
                print(f"Warning: Failed to process prompt point {i+1}: {e}")
                continue
        
        if not all_masks:
            raise RuntimeError("Failed to process any prompt points")
        
        # Combine all masks (union of all segmentations)
        combined_mask = all_masks[0]
        for additional_mask in all_masks[1:]:
            combined_mask = combined_mask | additional_mask
        mask = combined_mask
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate segmentation mask: {e}")
    
    print(f"Generated mask shape: {mask.shape}")
    print(f"Mask sum (total voxels segmented): {mask.sum()}")
    print(f"Mask dtype: {mask.dtype}")
    
    # Map mask back to original points
    point_locs = locs[inds_reconstruct]
    print(f"Point locations shape: {point_locs.shape}")
    print(f"Point locations min/max: {point_locs.min(axis=0)}, {point_locs.max(axis=0)}")
    print(f"Mask shape again: {mask.shape}")
    
    # Check if indices are within bounds
    valid_indices = (
        (point_locs[:, 0] >= 0) & (point_locs[:, 0] < mask.shape[0]) &
        (point_locs[:, 1] >= 0) & (point_locs[:, 1] < mask.shape[1]) &
        (point_locs[:, 2] >= 0) & (point_locs[:, 2] < mask.shape[2])
    )
    print(f"Valid indices: {valid_indices.sum()} out of {len(valid_indices)}")
    
    point_mask = mask[point_locs[:, 0], point_locs[:, 1], point_locs[:, 2]]
    
    print(f"Point mask shape: {point_mask.shape}")
    print(f"Point mask sum: {point_mask.sum()}")
    print(f"Segmented {point_mask.sum()} out of {len(point)} points")
    
    # Prepare output
    original_points, original_colors = read_ply(image_path)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Write the segmented PLY file
    write_ply(output_path, original_points, original_colors, point_mask.numpy())
    
    print(f"Segmentation completed! Output saved to: {output_path}")
    
    return point_mask


def main():
    """Main function to handle command line arguments and run segmentation."""
    parser = argparse.ArgumentParser(
        description="Segment 3D point clouds in PLY format using SAM2Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python segment_ply.py --image scene.ply --points prompts.ply --output result.ply
    python segment_ply.py --image data.ply --points points.ply --output out.ply --voxel-size 0.01
        """
    )
    
    parser.add_argument('--image', required=True, type=str,
                        help='Path to the input PLY point cloud file to segment')
    parser.add_argument('--points', required=True, type=str,
                        help='Path to the PLY file containing red-colored prompt points')
    parser.add_argument('--output', required=True, type=str,
                        help='Path to save the segmented PLY output file')
    parser.add_argument('--voxel-size', type=float, default=0.02,
                        help='Voxel size for processing (default: 0.02)')
    
    args = parser.parse_args()
    
    try:
        segment_ply_pointcloud(
            image_path=args.image,
            points_path=args.points,
            output_path=args.output,
            voxel_size=args.voxel_size
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())