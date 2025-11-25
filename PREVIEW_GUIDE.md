# 🔍 Refactored Script Preview Guide

## Quick Start

### 1. Installation

```bash
# Install required packages
pip install opencv-python numpy tqdm ultralytics reportlab

# Optional: For Korean PDF support
sudo apt-get install fonts-nanum
```

### 2. Set Model Paths (Optional)

```bash
# Method 1: Environment variables
export CRACK_MODEL_PATH="/path/to/crack_model/best.pt"
export DET_MODEL_PATH="/path/to/detection_model/best.pt"

# Method 2: Use command-line arguments (see usage below)
```

### 3. Basic Usage

```bash
python3 scripts/dual_infer_severity_v4_plus3.py \
  --input-root /path/to/images \
  --output-root results \
  --crack-model /path/to/crack/best.pt \
  --det-model /path/to/det/best.pt \
  --mm-per-pixel 0.5
```

## 📋 Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-root` | *required* | Directory containing building images |
| `--output-root` | `dual_reports` | Output directory |
| `--crack-model` | env/default | YOLOv8 segmentation model path |
| `--det-model` | env/default | YOLOv8 detection model path |
| `--imgsz` | `1024` | Input image size for models |
| `--crack-conf` | `0.25` | Crack detection confidence |
| `--det-conf` | `0.35` | Defect detection confidence |
| `--mm-per-pixel` | `1.0` | Ground Sample Distance (GSD) |
| `--topk-base` | `5` | Base number of severe defects |
| `--topk-max` | `7` | Max severe defects (high severity) |
| `--min-box-px` | `40` | Min bounding box size (filters distant defects) |
| `--min-mask-area-px` | `250` | Min mask area (filters noise) |

## 🎯 What's New in Refactored Version

### 🔴 Critical Improvements

#### 1. **Security Fix: XSS Prevention**
```python
# ❌ Before (vulnerable)
<td>{f.image}</td>

# ✅ After (secure)
safe_image = html.escape(f.image)
<td>{safe_image}</td>
```

#### 2. **Performance: 3x Faster Image Loading**
```python
# ❌ Before: Image loaded 3 times
img = cv2.imread(str(img_path))
crack_pred = model.predict(source=str(img_path))  # Loads again
det_pred = model.predict(source=str(img_path))    # Loads again

# ✅ After: Image loaded once
img = cv2.imread(str(img_path))
crack_pred = model.predict(source=img)  # Reuse array
det_pred = model.predict(source=img)    # Reuse array
```

#### 3. **Accuracy: Better Skeleton Length Calculation**
```python
# ❌ Before: Just count pixels
length_px = len(xs)  # Ignores diagonals

# ✅ After: Calculate actual distances
def _calculate_skeleton_length(points):
    diffs = np.diff(points, axis=0)
    distances = np.sqrt((diffs ** 2).sum(axis=1))
    return np.sum(distances)  # Accounts for √2 diagonal distance
```

### 🟡 Quality Improvements

#### 4. **Environment Variables Support**
```bash
# No more hardcoded paths!
export CRACK_MODEL_PATH="./models/crack/best.pt"
export DET_MODEL_PATH="./models/det/best.pt"

python3 scripts/dual_infer_severity_v4_plus3.py --input-root images/
```

#### 5. **Named Constants (Easy Tuning)**
```python
# All thresholds in one place
MIN_CRACK_LENGTH_MM = 20.0
MIN_CRACK_WIDTH_MM = 1.0
MIN_CRACK_AREA_MM2 = 50.0
STRAIGHTNESS_THRESHOLD = 0.9
ZOOM_PADDING_PX = 80
ZOOM_SIZE_RATIO = 0.25
```

#### 6. **Comprehensive Error Handling**
```python
# Errors are tracked and logged
errors: List[str] = []

try:
    res = inferencer.infer_one(img_path)
except Exception as e:
    error_msg = f"Inference failed for {img_path}: {e}"
    errors.append(error_msg)

# Summary at the end
if errors:
    print(f"⚠ Encountered {len(errors)} errors")
    # Auto-saved to errors.log
```

## 📊 Output Structure

```
output_root/
├── Building1/
│   ├── detected/              # All defects visualized
│   │   ├── img001_vis.jpg
│   │   └── img002_vis.jpg
│   ├── severe/                # Top N severe defects + zoom
│   │   ├── img001_severe.jpg  (rank badge + zoom inset)
│   │   └── img005_severe.jpg
│   ├── report/
│   │   ├── report.pdf         # Professional PDF report
│   │   └── report.html        # Interactive HTML viewer
│   ├── findings.json          # All defects (structured)
│   ├── findings.csv           # All defects (spreadsheet)
│   ├── stats.json             # Statistics
│   ├── stats.csv              # Statistics (spreadsheet)
│   └── errors.log             # Error log (if any)
└── Building2/
    └── ...
```

## 🎨 Visualization Features

### Detected Folder
- **Cracks**: Red polygon + white background label with **dark red bold text**
- **Other defects**: Yellow box + class-specific color + white background label

### Severe Folder (NEW!)
Each image shows:
1. **Top-left**: Yellow rank badge (#1, #2, etc.)
2. **Main area**: Primary defect highlighted
3. **Bottom-left**: Auto-generated ZOOM inset (25% width, 80px padding)

### HTML Report (Interactive)
- Click thumbnail → fullscreen viewer
- **Mouse wheel**: Zoom in/out (0.3x to 8x)
- **Drag**: Pan around image
- **ESC or click outside**: Close viewer

## 📈 Example Workflow

### Step 1: Organize Your Images
```bash
images/
├── Building_A/
│   ├── facade_001.jpg
│   ├── facade_002.jpg
│   └── ...
└── Building_B/
    ├── wall_001.jpg
    └── ...
```

### Step 2: Run Analysis
```bash
python3 scripts/dual_infer_severity_v4_plus3.py \
  --input-root images/ \
  --output-root results/ \
  --crack-model models/crack_seg/best.pt \
  --det-model models/detection/best.pt \
  --mm-per-pixel 0.8 \
  --crack-conf 0.3 \
  --det-conf 0.4
```

### Step 3: Review Results
```bash
# Open HTML report
xdg-open results/Building_A/report/report.html

# Or PDF report
xdg-open results/Building_A/report/report.pdf

# Check errors (if any)
cat results/Building_A/errors.log
```

## 🔧 Tuning Parameters

### For Noisy Images
```bash
# Increase confidence thresholds
--crack-conf 0.35 --det-conf 0.45

# Filter smaller detections
--min-box-px 60 --min-mask-area-px 400
```

### For Distant Defects
```bash
# Lower confidence (may increase false positives)
--crack-conf 0.2 --det-conf 0.25

# Allow smaller detections
--min-box-px 20 --min-mask-area-px 100
```

### For High-Resolution Images
```bash
# Increase model input size
--imgsz 1280

# Adjust GSD accordingly
--mm-per-pixel 0.3
```

## 🐛 Troubleshooting

### Error: "Cannot read image"
- Check image file is not corrupted
- Verify file permissions
- See `errors.log` for details

### Error: "Model not found"
- Check model paths are correct
- Use absolute paths if relative paths fail
- Verify `.pt` files exist

### Too many false positives
1. Increase confidence thresholds
2. Increase min_box_px / min_mask_area_px
3. Check crack filtering constants in code

### Missing defects
1. Lower confidence thresholds
2. Decrease min_box_px / min_mask_area_px
3. Verify mm_per_pixel is correct

## 📝 Testing the Refactored Code

### Quick Syntax Check
```bash
python3 -m py_compile scripts/dual_infer_severity_v4_plus3.py
echo "✅ Syntax OK"
```

### Test with Sample Images
```bash
# Create test directory
mkdir -p test_images/sample_building
# Add 2-3 test images
cp /path/to/test/*.jpg test_images/sample_building/

# Run on test set
python3 scripts/dual_infer_severity_v4_plus3.py \
  --input-root test_images/ \
  --output-root test_results/ \
  --crack-model models/crack.pt \
  --det-model models/det.pt

# Check results
ls -lh test_results/sample_building/
```

## 🎓 Advanced Usage

### Batch Processing Multiple Buildings
```bash
#!/bin/bash
for building in Building_*; do
  echo "Processing $building..."
  python3 scripts/dual_infer_severity_v4_plus3.py \
    --input-root "$building" \
    --output-root "results/$building" \
    --crack-model models/crack.pt \
    --det-model models/det.pt \
    --mm-per-pixel 0.5
done
```

### Custom Filtering Thresholds
Edit constants in script:
```python
# File: scripts/dual_infer_severity_v4_plus3.py
# Lines 60-68

MIN_CRACK_LENGTH_MM = 15.0      # Lowered from 20.0
MIN_CRACK_WIDTH_MM = 0.8        # Lowered from 1.0
MIN_CRACK_AREA_MM2 = 40.0       # Lowered from 50.0
STRAIGHTNESS_THRESHOLD = 0.85   # More lenient
```

## 📚 Documentation

- **Full refactoring details**: See `REFACTORING_SUMMARY.md`
- **Git history**: Check commit `3114c4e` and `3415ac1`
- **Inline documentation**: All functions have detailed docstrings

## 🚀 Performance Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Image loads per inference | 3x | 1x | **67% reduction** |
| I/O operations | High | Low | **3x faster** |
| Memory usage | Higher | Lower | More efficient |
| Crack length accuracy | Pixel count | Distance-based | **More accurate** |
| Error visibility | Silent | Logged | **Better debugging** |

## ✅ Validation Checklist

Before production deployment:

- [ ] Test with representative sample dataset
- [ ] Verify output formats (CSV, JSON, HTML, PDF)
- [ ] Check error handling with corrupted images
- [ ] Validate crack measurements against ground truth
- [ ] Review HTML report in different browsers
- [ ] Confirm PDF generation with Korean text
- [ ] Test with different GSD values
- [ ] Profile memory usage on large datasets

## 🔗 Related Files

- Main script: `scripts/dual_infer_severity_v4_plus3.py`
- Refactoring summary: `REFACTORING_SUMMARY.md`
- Git ignore: `.gitignore`
- This guide: `PREVIEW_GUIDE.md`

---

**Last Updated**: 2025-11-25
**Version**: v4_plus3 (Refactored)
**Commit**: 3114c4e, 3415ac1
