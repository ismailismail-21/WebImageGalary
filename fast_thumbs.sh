#!/bin/bash

# =============================================================================
# FAST THUMBNAIL GENERATOR
# Uses vipsthumbnail, gif2webp, ffmpeg with parallel processing
# =============================================================================

# CONFIGURATION - Change these paths
SOURCE_DIR="${1:-/media/user/DiskX/dataset}"
THUMB_DIR="${2:-./static/thumbs}"
SIZE="${3:-350}"
JOBS="${4:-$(nproc)}"  # Use all CPU cores by default

echo "=============================================="
echo "🚀 Fast Thumbnail Generator"
echo "=============================================="
echo "Source:     $SOURCE_DIR"
echo "Output:     $THUMB_DIR"
echo "Size:       ${SIZE}x${SIZE}"
echo "Jobs:       $JOBS parallel processes"
echo "=============================================="

# Check dependencies
check_deps() {
    local missing=()
    command -v vipsthumbnail >/dev/null || missing+=("libvips-tools")
    command -v gif2webp >/dev/null || missing+=("webp")
    command -v ffmpeg >/dev/null || missing+=("ffmpeg")
    command -v parallel >/dev/null || missing+=("parallel")
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo "❌ Missing dependencies: ${missing[*]}"
        echo "Install with: sudo apt install ${missing[*]}"
        exit 1
    fi
}

check_deps

# Validate source directory
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

mkdir -p "$THUMB_DIR"
cd "$SOURCE_DIR" || exit 1

# Count files
echo ""
echo "📊 Counting files..."
IMG_COUNT=$(find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) 2>/dev/null | wc -l)
GIF_COUNT=$(find . -type f -iname "*.gif" 2>/dev/null | wc -l)
VID_COUNT=$(find . -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) 2>/dev/null | wc -l)
echo "   Images: $IMG_COUNT"
echo "   GIFs:   $GIF_COUNT"  
echo "   Videos: $VID_COUNT"
echo "   Total:  $((IMG_COUNT + GIF_COUNT + VID_COUNT))"

# =============================================================================
# 1. REPLICATE FOLDER STRUCTURE
# =============================================================================
echo ""
echo "📂 Creating folder structure..."
find . -type d -exec mkdir -p "$THUMB_DIR/{}" \; 2>/dev/null

# =============================================================================
# 2. PROCESS STATIC IMAGES (JPG, PNG, WebP) - Parallel with vipsthumbnail
# =============================================================================
echo ""
echo "📸 Processing static images (parallel)..."

process_image() {
    local file="$1"
    local source_dir="$2"
    local thumb_dir="$3"
    local size="$4"
    
    # Get relative path and create output path
    local rel_path="${file#./}"
    local dir_path=$(dirname "$rel_path")
    local base_name=$(basename "$rel_path")
    local name_no_ext="${base_name%.*}"
    local output_dir="$thumb_dir/$dir_path"
    local output="$output_dir/${name_no_ext}.jpg"
    
    # Skip if exists
    [ -f "$output" ] && return 0
    
    # Create output directory
    mkdir -p "$output_dir"
    
    # Generate thumbnail with smart crop
    vipsthumbnail "$file" --size "${size}x${size}" --smartcrop attention -o "$output" 2>/dev/null
}
export -f process_image

find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) -print0 2>/dev/null | \
    parallel -0 -j "$JOBS" --bar process_image {} "$SOURCE_DIR" "$THUMB_DIR" "$SIZE"

# =============================================================================
# 3. PROCESS GIFs -> Animated WebP (Parallel)
# =============================================================================
echo ""
echo "🎞️ Processing GIFs to animated WebP (parallel)..."

process_gif() {
    local file="$1"
    local thumb_dir="$2"
    local size="$3"
    
    local rel_path="${file#./}"
    local dir_path=$(dirname "$rel_path")
    local base_name=$(basename "$rel_path")
    local name_no_ext="${base_name%.*}"
    local output_dir="$thumb_dir/$dir_path"
    local output="$output_dir/${name_no_ext}.webp"
    
    # Skip if exists
    [ -f "$output" ] && return 0
    
    mkdir -p "$output_dir"
    
    # First resize GIF, then convert to WebP
    # Using ffmpeg to resize and gif2webp for conversion
    local temp_gif="/tmp/temp_${name_no_ext}_$$.gif"
    
    ffmpeg -i "$file" -vf "scale=${size}:${size}:force_original_aspect_ratio=decrease,pad=${size}:${size}:(ow-iw)/2:(oh-ih)/2" \
        -y "$temp_gif" -loglevel error 2>/dev/null
    
    if [ -f "$temp_gif" ]; then
        gif2webp -q 70 -m 4 "$temp_gif" -o "$output" 2>/dev/null
        rm -f "$temp_gif"
    fi
}
export -f process_gif

find . -type f -iname "*.gif" -print0 2>/dev/null | \
    parallel -0 -j "$JOBS" --bar process_gif {} "$THUMB_DIR" "$SIZE"

# =============================================================================
# 4. PROCESS VIDEOS -> Static JPG Thumbnail (Parallel)
# =============================================================================
echo ""
echo "🎥 Processing videos (parallel)..."

process_video() {
    local file="$1"
    local thumb_dir="$2"
    local size="$3"
    
    local rel_path="${file#./}"
    local dir_path=$(dirname "$rel_path")
    local base_name=$(basename "$rel_path")
    local name_no_ext="${base_name%.*}"
    local output_dir="$thumb_dir/$dir_path"
    local output="$output_dir/${name_no_ext}.jpg"
    
    # Skip if exists
    [ -f "$output" ] && return 0
    
    mkdir -p "$output_dir"
    
    # Try to get frame at 5 seconds, fallback to 1 second if video is short
    ffmpeg -ss 00:00:05 -i "$file" -vframes 1 -q:v 2 \
        -vf "scale=${size}:${size}:force_original_aspect_ratio=increase,crop=${size}:${size}" \
        "$output" -y -loglevel error 2>/dev/null
    
    # If failed (video too short), try at 1 second
    if [ ! -f "$output" ]; then
        ffmpeg -ss 00:00:01 -i "$file" -vframes 1 -q:v 2 \
            -vf "scale=${size}:${size}:force_original_aspect_ratio=increase,crop=${size}:${size}" \
            "$output" -y -loglevel error 2>/dev/null
    fi
}
export -f process_video

find . -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) -print0 2>/dev/null | \
    parallel -0 -j "$JOBS" --bar process_video {} "$THUMB_DIR" "$SIZE"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=============================================="
THUMB_COUNT=$(find "$THUMB_DIR" -type f \( -iname "*.jpg" -o -iname "*.webp" \) 2>/dev/null | wc -l)
echo "✅ Done! Generated $THUMB_COUNT thumbnails"
echo "📁 Output: $THUMB_DIR"
echo "=============================================="
