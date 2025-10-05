rm -rf video
# Best voxel size found so far is 0.35: Segmented 9251 out of 20972 points
python3 segment_ply.py --image input/map_4400_1_colored2.ply --points input/combined_points_4400_1.ply --output output/sam2point_4400_1_colors.ply --voxel-size 0.35