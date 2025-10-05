# PLY Segmentation for SAM2Point

This document explains how to use the new PLY segmentation functionality with SAM2Point.

## Overview

The `segment_ply.py` script allows you to segment 3D point clouds in PLY format using positive and negative point prompts. Prompt points should be marked with specific colors in a separate PLY file:
- **Red (255, 0, 0)**: Positive prompts - points inside the object of interest
- **Green (0, 255, 0)**: Negative prompts - points in the background or regions to exclude

## Files Added

1. **`segment_ply.py`** - Main segmentation script for PLY files
2. **`sam2point/ply_utils.py`** - Utilities for reading/writing PLY files
3. **`create_test_data.py`** - Script to create test data for demonstration

## Usage

### Basic Command
```bash
python segment_ply.py --image scene.ply --points prompts.ply --output result.ply
```

### Arguments
- `--image`: Path to the input PLY point cloud file to segment
- `--points`: Path to the PLY file containing colored prompt points (red for positive, green for negative)
- `--output`: Path to save the segmented PLY output file
- `--voxel-size`: (Optional) Voxel size for processing (default: 0.02)

### Example with custom voxel size
```bash
python segment_ply.py --image data/scene.ply --points data/prompts.ply --output results/segmented.ply --voxel-size 0.01
```

The output will be white (255, 255, 255) for all points, with segmented regions in red (255, 0, 0).

## Running on Remote Server

### Prerequisites
1. Ensure all dependencies from `requirements.txt` are installed
2. Download the SAM2 model checkpoint:
   ```bash
   cd checkpoints
   bash download_ckpts.sh
   ```

### Step-by-Step Remote Execution

1. **Upload your files to the remote server:**
   ```bash
   scp image.ply points.ply user@remote-server:/path/to/SAM2Point/
   ```

2. **SSH into the remote server:**
   ```bash
   ssh user@remote-server
   cd /path/to/SAM2Point
   ```

3. **Set up the environment (if needed):**
   ```bash
   # If using conda
   conda activate sam2point_env
   
   # Or if using pip
   source venv/bin/activate
   ```

4. **Run the segmentation:**
   ```bash
   python segment_ply.py --image image.ply --points points.ply --output result.ply
   ```

5. **Download the result:**
   ```bash
   scp user@remote-server:/path/to/SAM2Point/result.ply ./
   ```

### Batch Processing
For multiple files, create a bash script:

```bash
#!/bin/bash
# batch_segment.sh

INPUT_DIR="input_data"
OUTPUT_DIR="results"
VOXEL_SIZE=0.02

mkdir -p $OUTPUT_DIR

for scene_file in $INPUT_DIR/*_scene.ply; do
    base_name=$(basename "$scene_file" _scene.ply)
    prompt_file="$INPUT_DIR/${base_name}_prompts.ply"
    output_file="$OUTPUT_DIR/${base_name}_segmented.ply"
    
    if [ -f "$prompt_file" ]; then
        echo "Processing $scene_file..."
        python segment_ply.py --image "$scene_file" --points "$prompt_file" --output "$output_file" --voxel-size $VOXEL_SIZE
    else
        echo "Warning: Prompt file $prompt_file not found, skipping $scene_file"
    fi
done
```

Run the batch script:
```bash
chmod +x batch_segment.sh
./batch_segment.sh
```

## Input File Requirements

### Scene PLY File (--image)
- Standard PLY format with vertex coordinates (x, y, z)
- Optional color information (red, green, blue)
- Any scale - will be automatically normalized

### Prompt PLY File (--points)
- Standard PLY format with vertex coordinates (x, y, z)
- **Must** include color information (red, green, blue)
- **Positive prompt points** must be colored **red (255, 0, 0)** - mark points inside the object
- **Negative prompt points** should be colored **green (0, 255, 0)** - mark background/exclude regions
- Other colored points will be ignored
- Should be in the same coordinate system as the scene file
- At least one red (positive) point is required; green (negative) points are optional

## Using Positive and Negative Points

### Positive Points (Red)
Positive points indicate regions you **want to segment**. Place red points:
- Inside the object of interest
- On surfaces you want to include
- In multiple locations for complex or ambiguous objects

### Negative Points (Green)
Negative points indicate regions you **want to exclude** from segmentation. Use green points to:
- Mark background regions
- Exclude nearby objects that might be accidentally included
- Refine segmentation boundaries
- Remove false positives

### Example Workflow
1. Start with red points on your object of interest
2. Run initial segmentation
3. If unwanted regions are included, add green points in those areas
4. Re-run segmentation with both red and green points for refined results

### Color Requirements
- **Red**: RGB(255, 0, 0) - Positive prompts
- **Green**: RGB(0, 255, 0) - Negative prompts
- Color tolerance is 50 by default (e.g., RGB(255, 20, 20) is still considered red)

## Output

The output PLY file contains:
- Original point coordinates from the scene
- **White color (255, 255, 255)** for all non-segmented points
- **Red color (255, 0, 0)** for segmented points

**Note:** The output creates a clean visualization with white background and red highlights for segmented regions. Prompt points are NOT included in the output.

## Testing

To test the functionality with sample data:

1. **Create test data:**
   ```bash
   python create_test_data.py
   ```

2. **Run segmentation on test data:**
   ```bash
   python segment_ply.py --image test_data/test_scene.ply --points test_data/test_prompts.ply --output test_data/result.ply
   ```

## Performance Tips

1. **Voxel Size**: Smaller voxel sizes provide higher resolution but take longer to process
2. **GPU Memory**: Large point clouds may require reducing voxel size or splitting the data
3. **Point Cloud Size**: For very large files, consider downsampling first

## Troubleshooting

### Common Issues

1. **"No red points found"**: Ensure positive prompt points are RGB (255, 0, 0) or within tolerance
2. **Segmentation includes unwanted regions**: Add green (negative) points in those areas
3. **Memory errors**: Try increasing voxel size (e.g., 0.05 instead of 0.02)
4. **CUDA errors**: Ensure GPU drivers and PyTorch CUDA are properly installed
5. **File not found**: Check file paths and ensure PLY files are valid
6. **Green points not working**: Verify green points are RGB (0, 255, 0) and contain color information

### Checking PLY Files
To verify your PLY files are valid:
```python
from sam2point.ply_utils import read_ply, extract_red_points, extract_green_points

# Check scene file
points, colors = read_ply('scene.ply')
print(f"Scene: {len(points)} points")

# Check prompt file
points, colors = read_ply('prompts.ply')
red_points = extract_red_points(points, colors)
green_points = extract_green_points(points, colors)
print(f"Prompts: {len(red_points)} red (positive) points found")
print(f"Prompts: {len(green_points)} green (negative) points found")
```

## Integration with Existing Workflow

This PLY functionality is designed to work alongside the existing SAM2Point capabilities. The core segmentation algorithm remains the same, with new I/O utilities to handle PLY format files.