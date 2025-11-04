#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch PLY Segmentation Script for SAM2Point

This script provides batch 3D point cloud segmentation functionality for PLY files.
It processes multiple pairs of files from an input folder, where each pair consists of:
- colored_XXXX_X.ply (the image/point cloud to segment)
- points_XXXX_X.ply (the prompt points file)

Output files are named prediction_XXXX_X.ply

Usage:
    python segment_ply_batch.py --input-folder /path/to/input --output-folder /path/to/output --voxel-size 0.35

The prompt points should be marked in red color (255, 0, 0) for positive prompts
and green color (0, 255, 0) for negative prompts in the points PLY files.
"""

import os
import glob
import argparse
import re
from pathlib import Path

# Import the segmentation function from the original script
from segment_ply import segment_ply_pointcloud


def find_file_pairs(input_folder):
    """
    Find pairs of colored_*.ply and points_*.ply files in the input folder.
    
    Args:
        input_folder (str): Path to the input folder
        
    Returns:
        list: List of tuples (colored_file, points_file, identifier)
    """
    input_path = Path(input_folder)
    
    # Find all colored_*.ply files
    colored_files = list(input_path.glob("colored_*.ply"))
    
    pairs = []
    for colored_file in colored_files:
        # Extract the identifier from the filename
        # colored_10274_1.ply -> 10274_1
        match = re.match(r'colored_(.+)\.ply$', colored_file.name)
        if match:
            identifier = match.group(1)
            points_file = input_path / f"points_{identifier}.ply"
            
            if points_file.exists():
                pairs.append((str(colored_file), str(points_file), identifier))
                print(f"Found pair: {colored_file.name} + {points_file.name} -> prediction_{identifier}.ply")
            else:
                print(f"Warning: Missing points file for {colored_file.name} (expected: {points_file.name})")
    
    return pairs


def process_batch(input_folder, output_folder, voxel_size=0.35):
    """
    Process all file pairs in the input folder.
    
    Args:
        input_folder (str): Path to the input folder containing file pairs
        output_folder (str): Path to the output folder for results
        voxel_size (float): Voxel size for processing
    """
    print(f"Processing batch segmentation...")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Voxel size: {voxel_size}")
    print("-" * 60)
    
    # Validate input folder
    if not os.path.exists(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all file pairs
    file_pairs = find_file_pairs(input_folder)
    
    if not file_pairs:
        print("No valid file pairs found in the input folder.")
        print("Expected format: colored_XXXX_X.ply and points_XXXX_X.ply")
        return
    
    print(f"Found {len(file_pairs)} file pairs to process")
    print("-" * 60)
    
    # Process each pair
    successful = 0
    failed = 0
    
    for i, (colored_file, points_file, identifier) in enumerate(file_pairs, 1):
        print(f"\nProcessing pair {i}/{len(file_pairs)}: {identifier}")
        print(f"  Image: {os.path.basename(colored_file)}")
        print(f"  Points: {os.path.basename(points_file)}")
        
        # Generate output filename
        output_file = os.path.join(output_folder, f"prediction_{identifier}.ply")
        print(f"  Output: {os.path.basename(output_file)}")
        
        try:
            # Process the pair
            segment_ply_pointcloud(
                image_path=colored_file,
                points_path=points_file,
                output_path=output_file,
                voxel_size=voxel_size
            )
            
            print(f"  ✓ Successfully processed {identifier}")
            successful += 1
            
        except Exception as e:
            print(f"  ✗ Failed to process {identifier}: {e}")
            failed += 1
            continue
    
    print("\n" + "=" * 60)
    print(f"Batch processing completed!")
    print(f"Successfully processed: {successful}/{len(file_pairs)}")
    print(f"Failed: {failed}/{len(file_pairs)}")
    print(f"Output folder: {output_folder}")


def main():
    """Main function to handle command line arguments and run batch segmentation."""
    parser = argparse.ArgumentParser(
        description="Batch segment 3D point clouds in PLY format using SAM2Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python segment_ply_batch.py --input-folder /path/to/input --output-folder /path/to/output
    python segment_ply_batch.py --input-folder ./data --output-folder ./results --voxel-size 0.35
    
Expected input file format:
    - colored_XXXX_X.ply (point cloud to segment)
    - points_XXXX_X.ply (prompt points with red=positive, green=negative)
    
Output file format:
    - prediction_XXXX_X.ply (segmentation result: white=background, red=segmented)
        """
    )
    
    parser.add_argument('--input-folder', required=True, type=str,
                        help='Path to the input folder containing PLY file pairs')
    parser.add_argument('--output-folder', required=True, type=str,
                        help='Path to the output folder for segmentation results')
    parser.add_argument('--voxel-size', type=float, default=0.35,
                        help='Voxel size for processing (default: 0.35)')
    
    args = parser.parse_args()
    
    try:
        process_batch(
            input_folder=args.input_folder,
            output_folder=args.output_folder,
            voxel_size=args.voxel_size
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())