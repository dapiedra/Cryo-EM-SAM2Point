# Negative Point Support Implementation Summary

## Overview
Added support for negative point prompts in SAM2Point PLY segmentation. Users can now mark regions to exclude from segmentation using green-colored points, in addition to positive (red) points.

## Files Modified

### 1. `sam2point/ply_utils.py`
**Added:**
- `extract_green_points()` function - Extracts green-colored points (RGB 0, 255, 0) as negative prompts
- Similar to `extract_red_points()` but checks for predominantly green color

### 2. `segment.py`
**Modified:**
- `segment_point()` function now accepts `negative_points` parameter
- Constructs proper labels array: `1` for positive points, `0` for negative points
- Concatenates positive and negative points before passing to SAM2 predictor

**Modified:**
- `seg_point()` function now accepts `negative_prompt` parameter
- Converts negative prompts to voxel and pixel coordinates
- Passes negative points to `segment_point()` for all three axes (x, y, z)

### 3. `segment_ply.py`
**Modified:**
- Import `extract_green_points` from `ply_utils`
- Extract green points in addition to red points from prompt file
- Normalize green points using same transformation as scene points
- Validate green points are within voxel bounds
- Pass negative prompts to `seg_point()` function
- Updated console output to distinguish positive/negative points

### 4. `PLY_SEGMENTATION_README.md`
**Updated:**
- Overview section explains both positive (red) and negative (green) points
- Added detailed "Using Positive and Negative Points" section with:
  - When to use positive points
  - When to use negative points
  - Example workflow
  - Color requirements
- Updated troubleshooting section
- Updated verification code example to include green point extraction

### 5. `test_negative_points.py` (Optional)
**Can be created:**
- Test script to verify negative point extraction
- Creates sample PLY file with both red and green points
- Validates extraction functions work correctly
- Provides usage instructions

## How It Works

### Color Coding
- **Red (255, 0, 0)**: Positive prompts - mark points inside objects of interest
- **Green (0, 255, 0)**: Negative prompts - mark background or regions to exclude
- Color tolerance: 50 (configurable)

### Implementation Flow
1. User creates PLY file with red and green colored points
2. `segment_ply.py` reads the file and extracts both colors separately
3. Points are normalized to match scene coordinate system
4. Both positive and negative points are validated against voxel bounds
5. `seg_point()` converts points to voxel/pixel coordinates
6. For each axis, `segment_point()` is called with:
   - One positive point (the primary prompt)
   - All negative points
7. SAM2 predictor receives combined points array with proper labels:
   - `labels[i] = 1` for positive points
   - `labels[i] = 0` for negative points
8. SAM2 uses negative points to refine segmentation boundaries
9. Results are combined across all axes

### SAM2 Integration
The implementation leverages SAM2's native support for negative points:
- `point_labels = 1` → foreground/positive
- `point_labels = 0` → background/negative

This is handled in SAM2's prompt encoder (`sam2/modeling/sam/prompt_encoder.py`)

## Usage Example

```bash
# Create a prompt file with:
# - Red points (255, 0, 0) on the object you want to segment
# - Green points (0, 255, 0) on background or regions to exclude

python segment_ply.py \
    --image input/scene.ply \
    --points input/prompts_with_negatives.ply \
    --output output/segmented.ply \
    --voxel-size 0.06
```

### Example with Real Data
Using the provided example file:
```bash
python segment_ply.py \
    --image input/map_4400_1.ply \
    --points input/combined_points_4400_1.ply \
    --output output/segmented_4400_1.ply \
    --voxel-size 0.06
```

The file `combined_points_4400_1.ply` contains:
- 3 red points (positive prompts)
- 8 green points (negative prompts)

## Benefits

1. **Better Accuracy**: Exclude unwanted regions that might be accidentally included
2. **Boundary Refinement**: Fine-tune segmentation edges
3. **False Positive Reduction**: Remove incorrectly segmented areas
4. **Flexibility**: Start with positive points only, add negatives as needed

## Testing

You can verify the implementation works by checking the extraction functions:
```python
from sam2point.ply_utils import read_ply, extract_red_points, extract_green_points

# Test with the provided example file
points, colors = read_ply('input/combined_points_4400_1.ply')
red_points = extract_red_points(points, colors)
green_points = extract_green_points(points, colors)

print(f"Red (positive) points: {len(red_points)}")  # Should be 3
print(f"Green (negative) points: {len(green_points)}")  # Should be 8
```

## Backward Compatibility

✅ Fully backward compatible!
- Existing workflows using only red points continue to work
- Green points are optional
- If no green points are found, the system works exactly as before

## Future Enhancements

Potential improvements:
- Support for additional color-coded prompt types
- Adjustable color tolerance per point type
- Batch processing with different negative point sets
- Visualization of prompt points in output
