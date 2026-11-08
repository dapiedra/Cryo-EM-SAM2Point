#!/bin/bash

# Batch PLY processing script
# This script processes multiple pairs of PLY files from an input folder

# Remove any existing video output
rm -rf video

# Configuration
INPUT_FOLDER="/work/dpierdra/datasets/dataset_full/grayscale/test_data_input_5p_5n"
OUTPUT_FOLDER="/work/dpierdra/results/grayscale/SAM2Point/5p_5n/output_ply"

# Best is 0.25
#VOXEL_SIZE=0.35
VOXEL_SIZE=0.25

echo "Running batch PLY segmentation..."
echo "Input folder: $INPUT_FOLDER"
echo "Output folder: $OUTPUT_FOLDER"
echo "Voxel size: $VOXEL_SIZE"

# Run the batch processing
python3 segment_ply_batch.py \
    --input-folder "$INPUT_FOLDER" \
    --output-folder "$OUTPUT_FOLDER" \
    --voxel-size "$VOXEL_SIZE"

echo "Batch processing completed!"