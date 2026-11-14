#!/bin/bash

# Batch PLY processing script
# This script processes multiple pairs of PLY files from input folders.
# It iterates over every experiment (test_data_input_<exp>/<iteration>) and
# iterations 1 to 3 of each experiment. Iterations 4 and 5 are ignored.

# Remove any existing video output
rm -rf video

# Configuration
BASE_DIR="/work/dpierdra/datasets/dataset_full/multiple_iterations"
# Folder containing the colored_*.ply / map_*.ply source files shared by all runs.
# Searched when a file is not found in the input folder.
# Leave empty to disable the fallback.
MAPS_FOLDER="${BASE_DIR}/colored_input"
OUTPUT_BASE_DIR="${BASE_DIR}/output_sam2point"

# Best is 0.25
#VOXEL_SIZE=0.35
VOXEL_SIZE=0.25

# Experiments to process (input folders are test_data_input_<experiment>/<iteration>)
#EXPERIMENTS=("5p_5n" "20p_5n" "5p_20n" "20p_15n")
EXPERIMENTS=("20p_5n")

# Iterations to process per experiment (4 and 5 are ignored)
ITERATIONS=(1 2 3)

echo "Running batch PLY segmentation..."
echo "Voxel size: $VOXEL_SIZE"

for EXP in "${EXPERIMENTS[@]}"; do
    for ITER in "${ITERATIONS[@]}"; do
        INPUT_FOLDER="${BASE_DIR}/test_data_input_${EXP}/${ITER}"
        OUTPUT_FOLDER="${OUTPUT_BASE_DIR}/${EXP}/${ITER}"

        if [ ! -d "$INPUT_FOLDER" ]; then
            echo "Skipping ${EXP} iteration ${ITER}: input folder not found: ${INPUT_FOLDER}"
            continue
        fi

        echo
        echo "=== Experiment: ${EXP} | Iteration: ${ITER} ==="
        echo "Input folder: $INPUT_FOLDER"
        if [ -n "$MAPS_FOLDER" ]; then
            echo "Fallback maps folder: $MAPS_FOLDER"
        fi
        echo "Output folder: $OUTPUT_FOLDER"

        # Run the batch processing
        ARGS=(
            --input-folder "$INPUT_FOLDER"
            --output-folder "$OUTPUT_FOLDER"
            --voxel-size "$VOXEL_SIZE"
        )
        if [ -n "$MAPS_FOLDER" ]; then
            ARGS+=(--maps-folder "$MAPS_FOLDER")
        fi

        python3 segment_ply_batch.py "${ARGS[@]}"
    done
done

echo "Batch processing completed!"
