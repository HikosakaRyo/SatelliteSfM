#!/bin/bash

# Post-processing script for a single satellite scene.
# Performs: skew correction, dataset conversion, points3D copy, and mask generation.
#
# Usage:
#   ./postprocess_scene.sh <SCENE_NAME> [OPTIONS]
#
# Examples:
#   ./postprocess_scene.sh BSG-STEREO-MF-117-20260114-023900-417077014
#   ./postprocess_scene.sh BSG-STEREO-MF-117-20260114-023900-417077014 --skip-skew
#   ./postprocess_scene.sh BSG-STEREO-MF-117-20260114-023900-417077014 --dry-run

set -euo pipefail

# ============================================================
# Configuration
# ============================================================
SCENE="${1:-}"
BASE_DIR="outputs"
LOG_DIR="logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step flags
SKIP_SKEW=false
SKIP_CONVERT=false
SKIP_COPY=false
SKIP_MASK=false
DRY_RUN=false

# ============================================================
# Usage
# ============================================================
usage() {
    cat <<EOF
Usage: $0 <SCENE_NAME> [OPTIONS]

Arguments:
  SCENE_NAME            Scene directory name (e.g., BSG-STEREO-MF-117-20260114-023900-417077014)

Options:
  --base-dir DIR        Base directory containing scene output (default: outputs)
  --skip-skew           Skip Step 1: skew correction
  --skip-convert        Skip Step 2: dataset conversion
  --skip-copy           Skip Step 3: points3D.txt copy
  --skip-mask           Skip Step 4: mask generation
  --dry-run             Print commands without executing
  -h, --help            Show this help message

Logs are written to: ${LOG_DIR}/<SCENE>_step<N>_<YYYYMMDD-HHMMSS>.log
EOF
}

# ============================================================
# Parse arguments
# ============================================================
if [[ -z "$SCENE" || "$SCENE" == -* ]]; then
    echo -e "${RED}Error: SCENE_NAME is required as the first argument.${NC}"
    usage
    exit 1
fi
shift  # consume SCENE

while [[ $# -gt 0 ]]; do
    case $1 in
        --base-dir)   BASE_DIR="$2"; shift 2 ;;
        --skip-skew)  SKIP_SKEW=true;  shift ;;
        --skip-convert) SKIP_CONVERT=true; shift ;;
        --skip-copy)  SKIP_COPY=true;  shift ;;
        --skip-mask)  SKIP_MASK=true;  shift ;;
        --dry-run)    DRY_RUN=true;    shift ;;
        -h|--help)    usage; exit 0 ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# ============================================================
# Derived paths
# ============================================================
SCENE_DIR="${BASE_DIR}/${SCENE}"
INPUT_FOLDER="${SCENE_DIR}/outputs_srtm"
OUTPUT_FOLDER="${SCENE_DIR}/outputs_skew"
POINTS3D_SRC="${INPUT_FOLDER}/colmap_triangulate_postba/points3D.txt"
POINTS3D_DST="${OUTPUT_FOLDER}/points3D.txt"
IMAGES_DIR="${OUTPUT_FOLDER}/images"
MASKS_DIR="${OUTPUT_FOLDER}/masks"

# ============================================================
# Helpers
# ============================================================
mkdir -p "$LOG_DIR"

make_logfile() {
    local step_num="$1"
    local step_name="$2"
    local ts
    ts=$(date +"%Y%m%d-%H%M%S")
    echo "${LOG_DIR}/${SCENE}_step${step_num}_${step_name}_${ts}.log"
}

run_step() {
    # run_step <step_num> <step_name> <command ...>
    local step_num="$1"; shift
    local step_name="$1"; shift
    local logfile
    logfile=$(make_logfile "$step_num" "$step_name")

    echo ""
    echo -e "${GREEN}--- Step ${step_num}: ${step_name} ---${NC}"
    echo "  Log: ${logfile}"

    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}[DRY RUN]${NC} $*"
        echo "[DRY RUN] $*" > "$logfile"
        return 0
    fi

    echo "  Command: $*"
    echo "========== $(date) ==========" > "$logfile"
    echo "Command: $*" >> "$logfile"
    echo "" >> "$logfile"

    if "$@" >> "$logfile" 2>&1; then
        echo -e "${GREEN}  ✓ Step ${step_num} succeeded${NC}"
        echo "" >> "$logfile"
        echo "========== RESULT: SUCCESS ($(date)) ==========" >> "$logfile"
        return 0
    else
        local rc=$?
        echo -e "${RED}  ✗ Step ${step_num} FAILED (exit code ${rc})${NC}"
        echo "" >> "$logfile"
        echo "========== RESULT: FAILED exit=${rc} ($(date)) ==========" >> "$logfile"
        echo -e "${RED}  See log for details: ${logfile}${NC}"
        return $rc
    fi
}

# ============================================================
# Validation
# ============================================================
echo ""
echo "=========================================="
echo -e "${GREEN}Post-processing scene: ${SCENE}${NC}"
echo "=========================================="
echo "  Base dir     : ${BASE_DIR}"
echo "  Input folder : ${INPUT_FOLDER}"
echo "  Output folder: ${OUTPUT_FOLDER}"

if [[ ! -d "$INPUT_FOLDER" ]]; then
    echo -e "${RED}Error: Input folder does not exist: ${INPUT_FOLDER}${NC}"
    exit 1
fi

# ============================================================
# Step 1: Skew correction
# ============================================================
if [[ "$SKIP_SKEW" == false ]]; then
    run_step 1 skew_correct \
        python skew_correct.py \
            --input_folder "$INPUT_FOLDER" \
            --output_folder "$OUTPUT_FOLDER"
else
    echo -e "${YELLOW}Step 1: Skipping skew correction${NC}"
fi

# ============================================================
# Step 2: Dataset conversion
# ============================================================
if [[ "$SKIP_CONVERT" == false ]]; then
    run_step 2 convert_datasets \
        python convert_datasets.py \
            --input_folder "$OUTPUT_FOLDER"
else
    echo -e "${YELLOW}Step 2: Skipping dataset conversion${NC}"
fi

# ============================================================
# Step 3: Copy points3D.txt
# ============================================================
if [[ "$SKIP_COPY" == false ]]; then
    if [[ -f "$POINTS3D_SRC" ]]; then
        run_step 3 copy_points3D \
            cp "$POINTS3D_SRC" "$POINTS3D_DST"
    else
        echo -e "${YELLOW}Step 3: Source not found, skipping: ${POINTS3D_SRC}${NC}"
    fi
else
    echo -e "${YELLOW}Step 3: Skipping points3D.txt copy${NC}"
fi

# ============================================================
# Step 4: Generate masks
# ============================================================
if [[ "$SKIP_MASK" == false ]]; then
    if [[ -d "$IMAGES_DIR" ]]; then
        run_step 4 generate_masks \
            python generate_masks.py \
                --input_dir "$IMAGES_DIR" \
                --output_dir "$MASKS_DIR"
    else
        echo -e "${YELLOW}Step 4: Images dir not found, skipping: ${IMAGES_DIR}${NC}"
    fi
else
    echo -e "${YELLOW}Step 4: Skipping mask generation${NC}"
fi

# ============================================================
# Done
# ============================================================
echo ""
echo "=========================================="
echo -e "${GREEN}Post-processing complete for: ${SCENE}${NC}"
echo "Logs are in: ${LOG_DIR}/"
echo "=========================================="
