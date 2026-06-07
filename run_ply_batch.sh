#!/bin/bash

# Batch PLY processing script
# This script processes multiple pairs of PLY files from an input folder

# Remove any existing video output
rm -rf video

# Configuration
INPUT_FOLDER="/work/dpierdra/datasets/dataset_full/test_data_input_20p_10n_no_thr"
OUTPUT_FOLDER="/work/dpierdra/SAM2Point/output_20p_10n_no_thr"

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