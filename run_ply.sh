rm -rf video
# Best voxel size found so far is 0.35: Segmented 9251 out of 20972 points
python3 segment_ply.py --image /work/dpierdra/datasets/4156_contour/colored_4156_1.ply --points /work/dpierdra/datasets/4156_contour/points_4156_1.ply --output output/sam2point_pred_4156_1.ply --voxel-size 0.25