#!/usr/bin/env bash
# ============================================================================
# download_model.sh — Pre-download YOLOv8n model for bottle detection
#
# ultralytics auto-downloads on first run, but this script lets you
# pre-cache the model so the node starts instantly.
#
# COCO class 39 = "bottle" — covers water bottles, soda bottles, etc.
# Model size: ~6 MB
#
# Usage:
#   bash tools/download_model.sh
# ============================================================================
set -euo pipefail

python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # downloads if not cached
print('YOLOv8n ready:', model.ckpt_path)
"
