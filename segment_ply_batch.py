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
    python segment_ply_batch.py --input-folder /path/to/input --maps-folder /path/to/maps --output-folder /path/to/output

The prompt points should be marked in red color (255, 0, 0) for positive prompts
and green color (0, 255, 0) for negative prompts in the points PLY files.
"""

import os
import glob
import argparse
import re
import gc
import torch
from pathlib import Path

# Import the segmentation function from the original script
from segment_ply import segment_ply_pointcloud

# Import model building for predictor management
from sam2.build_sam import build_sam2_video_predictor
from segment import CHECKPOINT, MODELCFG


def find_file_pairs(input_folder, maps_folders=None):
    """
    Find pairs of colored_*.ply / map_*.ply and points_*.ply files.

    The colored_/map_ source files are looked up first in the input folder,
    then in each of the optional maps_folders (in the order given, first
    match wins per identifier). points_*.ply files are only looked up in the
    input folder. For each identifier, colored_ is preferred over map_ across
    all search folders.

    Args:
        input_folder (str): Path to the input folder (points_*.ply always come
            from here)
        maps_folders (list): Optional extra folders searched for
            colored_*.ply / map_*.ply files missing from the input folder

    Returns:
        list: List of tuples (source_file, points_file, identifier)
    """
    input_path = Path(input_folder)
    search_folders = [input_path] + [Path(f) for f in (maps_folders or [])]

    def index_by_identifier(path, prefix):
        """Index files per identifier; first folder wins for duplicate names."""
        indexed = {}
        for source_file in sorted(path.glob(f"{prefix}*.ply")):
            match = re.match(rf'{prefix}(.+)\.ply$', source_file.name)
            if match:
                indexed.setdefault(match.group(1), source_file)
        return indexed

    colored = {}
    maps = {}
    points = {}
    for folder in search_folders:
        if not folder.is_dir():
            print(f"Warning: search folder not found, skipping: {folder}")
            continue
        found_colored = index_by_identifier(folder, "colored_")
        found_maps = index_by_identifier(folder, "map_")
        for identifier, file in found_colored.items():
            colored.setdefault(identifier, file)
        for identifier, file in found_maps.items():
            maps.setdefault(identifier, file)
    # points_ files are only paired from the input folder
    points = index_by_identifier(input_path, "points_")

    pairs = []
    for identifier in sorted(set(colored) | set(maps)):
        # Per-identifier preference: colored_ anywhere before map_
        source_file = colored.get(identifier) or maps.get(identifier)
        points_file = points.get(identifier)

        if points_file is not None:
            pairs.append((str(source_file), str(points_file), identifier))
            print(f"Found pair: {source_file.name} (from {source_file.parent}) + "
                  f"{points_file.name} -> prediction_{identifier}.ply")
        else:
            print(f"Warning: Missing points file for {source_file.name} "
                  f"(expected: points_{identifier}.ply in {input_path})")

    if not pairs:
        print("No valid colored_ or map_ file pairs found.")
    return pairs


def process_batch(input_folder, output_folder, voxel_size=0.35, maps_folders=None):
    """
    Process all file pairs in the input folder.
    
    Args:
        input_folder (str): Path to the input folder containing points_*.ply files
        output_folder (str): Path to the output folder for results
        voxel_size (float): Voxel size for processing
        maps_folders (list): Optional extra folders searched for
            colored_/map_ files missing from the input folder
    """
    print(f"Processing batch segmentation...")
    print(f"Input folder: {input_folder}")
    if maps_folders:
        print(f"Extra maps folders: {', '.join(maps_folders)}")
    print(f"Output folder: {output_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Voxel size: {voxel_size}")
    print("-" * 60)
    
    # Validate input folder
    if not os.path.exists(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all file pairs
    file_pairs = find_file_pairs(input_folder, maps_folders)

    if not file_pairs:
        print("No valid file pairs found.")
        print("Expected format: colored_XXXX_X.ply (or map_XXXX_X.ply) + points_XXXX_X.ply")
        return
    
    print(f"Found {len(file_pairs)} file pairs to process")
    print("-" * 60)
    
    # Check for existing predictions and filter out already processed files
    files_to_process = []
    skipped = 0
    
    for colored_file, points_file, identifier in file_pairs:
        output_file = os.path.join(output_folder, f"prediction_{identifier}.ply")
        if os.path.exists(output_file):
            print(f"Skipping {identifier} (prediction already exists)")
            skipped += 1
        else:
            files_to_process.append((colored_file, points_file, identifier))
    
    if skipped > 0:
        print(f"\nSkipped {skipped} already processed file(s)")
    
    if not files_to_process:
        print("\nAll files have already been processed. Nothing to do.")
        return
    
    print(f"\nRemaining files to process: {len(files_to_process)}")
    print("-" * 60)
    
    # MEMORY OPTIMIZATION: Create predictor once and reuse for all files
    # This is the KEY to preventing OOM errors in batch processing
    print("Loading SAM2 model (this will be reused for all files to save memory)...")
    predictor = build_sam2_video_predictor(MODELCFG, CHECKPOINT)
    print("Model loaded successfully!")
    print("-" * 60)
    
    # Process each pair
    successful = 0
    failed = 0
    
    try:
        for i, (colored_file, points_file, identifier) in enumerate(files_to_process, 1):
            print(f"\nProcessing pair {i}/{len(files_to_process)}: {identifier}")
            print(f"  Image: {os.path.basename(colored_file)}")
            print(f"  Points: {os.path.basename(points_file)}")
            
            # Generate output filename
            output_file = os.path.join(output_folder, f"prediction_{identifier}.ply")
            print(f"  Output: {os.path.basename(output_file)}")
            
            try:
                # Process the pair with the shared predictor
                segment_ply_pointcloud(
                    image_path=colored_file,
                    points_path=points_file,
                    output_path=output_file,
                    voxel_size=voxel_size,
                    predictor=predictor  # Reuse the same predictor for all files
                )
                
                print(f"  ✓ Successfully processed {identifier}")
                successful += 1
                
                # CRITICAL: Clear GPU memory after each pair to prevent OOM errors
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                gc.collect()
                
            except Exception as e:
                print(f"  ✗ Failed to process {identifier}: {e}")
                failed += 1
                
                # Still clear GPU memory even after failure
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                gc.collect()
                
                continue
    finally:
        # Clean up the shared predictor at the end
        print("\nCleaning up model...")
        del predictor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
    
    print("\n" + "=" * 60)
    print(f"Batch processing completed!")
    if skipped > 0:
        print(f"Skipped (already processed): {skipped}")
    print(f"Successfully processed: {successful}/{len(files_to_process)}")
    print(f"Failed: {failed}/{len(files_to_process)}")
    print(f"Total files in input folder: {len(file_pairs)}")
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
    python segment_ply_batch.py --input-folder ./points --maps-folder ./maps --output-folder ./results
    
Expected input file format:
    - colored_XXXX_X.ply (point cloud to segment)
    - points_XXXX_X.ply (prompt points with red=positive, green=negative)
    
Output file format:
    - prediction_XXXX_X.ply (segmentation result: white=background, red=segmented)
        """
    )
    
    parser.add_argument('--input-folder', required=True, type=str,
                        help='Path to the input folder containing PLY file pairs')
    parser.add_argument('--maps-folder', action='append', type=str, default=[],
                        help='Extra folder searched for colored_*.ply / map_*.ply files '
                             'when not found in the input folder. Can be passed multiple times; '
                             'searched in the order given.')
    parser.add_argument('--output-folder', required=True, type=str,
                        help='Path to the output folder for segmentation results')
    parser.add_argument('--voxel-size', type=float, default=0.35,
                        help='Voxel size for processing (default: 0.35)')
    
    args = parser.parse_args()
    
    try:
        process_batch(
            input_folder=args.input_folder,
            output_folder=args.output_folder,
            voxel_size=args.voxel_size,
            maps_folders=args.maps_folder
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())