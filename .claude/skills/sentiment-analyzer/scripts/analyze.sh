#!/usr/bin/env bash
# Sentiment Analyzer Wrapper
# Calls the original sentiment-analyzer-engine from Obsidian skills

set -euo pipefail

# Configuration
ENGINE_DIR="/Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa"
VENV_DIR="${ENGINE_DIR}/.venv"
ANALYZE_SCRIPT="/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sentiment-analyzer-engine/scripts/analyze.py"
CONFIGS_DIR="/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sentiment-analyzer-engine/configs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check prerequisites
check_prerequisites() {
    # Check if Python venv exists
    if [[ ! -d "${VENV_DIR}" ]]; then
        log_error "Python virtual environment not found at: ${VENV_DIR}"
        log_info "Please run: cd ${ENGINE_DIR} && uv sync"
        exit 1
    fi

    # Check if analyze script exists
    if [[ ! -f "${ANALYZE_SCRIPT}" ]]; then
        log_error "Analyze script not found at: ${ANALYZE_SCRIPT}"
        exit 1
    fi

    # Check if configs directory exists
    if [[ ! -d "${CONFIGS_DIR}" ]]; then
        log_warn "Configs directory not found at: ${CONFIGS_DIR}"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Sentiment Analyzer - Universal sentiment analysis engine

Usage: analyze.sh [OPTIONS]

Options:
  --text TEXT           Single text to analyze
  --file FILE           JSON file with multiple texts/items
  --config CONFIG       Configuration preset (default: default)
                        Available: financial, social_media, product_review, default
  --mode MODE           Analysis mode (default: auto)
                        Available: keyword, ai, auto
  --weighted            Enable weighted aggregation (requires source + timestamp in input)
  --output FILE         Save results to JSON file
  --help                Show this help message

Examples:
  # Analyze single text
  analyze.sh --text "Great product!" --config product_review

  # Batch analyze with file
  analyze.sh --file reviews.json --config social_media --mode ai

  # Weighted aggregation
  analyze.sh --file news.json --config financial --weighted --output result.json

Config presets:
  - financial:   Stock news, earnings reports, finance content
  - social_media: Twitter, Reddit, forums, social posts
  - product_review: Amazon, Yelp, customer reviews
  - default:     General text analysis

EOF
}

# Parse arguments
TEXT=""
FILE=""
CONFIG="default"
MODE="auto"
WEIGHTED=false
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --text)
            TEXT="$2"
            shift 2
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --weighted)
            WEIGHTED=true
            shift
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ -z "${TEXT}" && -z "${FILE}" ]]; then
    log_error "Either --text or --file must be specified"
    show_usage
    exit 1
fi

# Check prerequisites
check_prerequisites

# Activate virtual environment and run analysis
log_info "Running sentiment analysis..."
log_info "Config: ${CONFIG} | Mode: ${MODE}"

# Build command
CMD_ARGS=(
    "--config" "${CONFIG}"
    "--mode" "${MODE}"
)

if [[ -n "${TEXT}" ]]; then
    CMD_ARGS+=("--text" "${TEXT}")
fi

if [[ -n "${FILE}" ]]; then
    if [[ ! -f "${FILE}" ]]; then
        log_error "File not found: ${FILE}"
        exit 1
    fi
    CMD_ARGS+=("--file" "${FILE}")
fi

if [[ "${WEIGHTED}" == true ]]; then
    CMD_ARGS+=("--weighted")
fi

if [[ -n "${OUTPUT}" ]]; then
    CMD_ARGS+=("--output" "${OUTPUT}")
    log_info "Output will be saved to: ${OUTPUT}"
fi

# Activate venv and run
source "${VENV_DIR}/bin/activate"

# Run the original analyze script
cd "${ENGINE_DIR}"
python3 "${ANALYZE_SCRIPT}" "${CMD_ARGS[@]}"

deactivate

log_info "Analysis complete!"
