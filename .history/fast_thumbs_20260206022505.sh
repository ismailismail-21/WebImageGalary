#!/bin/bash

# =============================================================================
# FAST THUMBNAIL GENERATOR
# Creates thumbnails in a 'thumbnails' subfolder within each image's folder
# Uses vipsthumbnail, gif2webp, ffmpeg with parallel processing
# =============================================================================

# CONFIGURATION
SOURCE_DIR="${1:-/media/user/DiskX/dataset}"
SIZE="${2:-350}"
JOBS="${3:-$(nproc)}"  # Use all CPU cores by default

echo "=============================================="
echo "🚀 Fast Thumbnail Generator"
echo "=============================================="
echo "Source:     $SOURCE_DIR"
echo "Size:       ${SIZE}x${SIZE}"
echo "Jobs:       $JOBS parallel processes"
echo "Thumbs:     Created in each folder's 'thumbnails' subfolder"
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
    echo "✅ All dependencies found"
}

check_deps

# Validate source directory
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

cd "$SOURCE_DIR" || exit 1

# Count files
echo ""
echo "📊 Counting files..."
IMG_COUNT=$(find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) ! -path "*/thumbnails/*" 2>/dev/null | wc -l)
GIF_COUNT=$(find . -type f -iname "*.gif" ! -path "*/thumbnails/*" 2>/dev/null | wc -l)
VID_COUNT=$(find . -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) ! -path "*/thumbnails/*" 2>/dev/null | wc -l)
TOTAL=$((IMG_COUNT + GIF_COUNT + VID_COUNT))
echo "   📸 Images: $IMG_COUNT"
echo "   🎞️  GIFs:   $GIF_COUNT"  
echo "   🎥 Videos: $VID_COUNT"
echo "   📁 Total:  $TOTAL"

# =============================================================================
# 2. PROCESS STATIC IMAGES (JPG, PNG, WebP) - Parallel with vipsthumbnail
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📸 [1/3] Processing Static Images..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

process_image() {
    local file="$1"
    local size="$2"
    
    # Get directory and filename
    local dir_path
    local base_name
    local name_no_ext
    dir_path="$(dirname "$file")"
    base_name="$(basename "$file")"
    name_no_ext="${base_name%.*}"
    
    # Create thumbnails folder in same directory
    local thumb_dir="$dir_path/thumbnails"
    local output="$thumb_dir/${name_no_ext}.jpg"
    
    # Skip if exists
    if [ -f "$output" ]; then
        echo "SKIP: $base_name"
        return 0
    fi
    
    # Create output directory
    mkdir -p "$thumb_dir"
    
    # Generate thumbnail with ImageMagick - center crop to square
    if convert "$file" -thumbnail "${size}x${size}^" -gravity center -extent "${size}x${size}" -quality 85 "$output" 2>/dev/null; then
        echo "✓ $base_name"
    else
        echo "✗ $base_name (failed)"
    fi
}
export -f process_image

# Count existing thumbnails for images
IMG_EXISTING=$(find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) ! -path "*/thumbnails/*" 2>/dev/null | while read f; do
    dir=$(dirname "$f")
    name=$(basename "${f%.*}")
    [ -f "$dir/thumbnails/${name}.jpg" ] && echo "1"
done | wc -l)
IMG_TODO=$((IMG_COUNT - IMG_EXISTING))
echo "   Already done: $IMG_EXISTING, To process: $IMG_TODO"

if [ "$IMG_TODO" -gt 0 ]; then
    find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) ! -path "*/thumbnails/*" -print0 2>/dev/null | \
        parallel -0 -j "$JOBS" --bar --eta process_image {} "$SIZE"
else
    echo "   ✅ All images already have thumbnails"
fi

# =============================================================================
# 3. PROCESS GIFs -> Animated WebP (Parallel)
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎞️  [2/3] Processing GIFs to Animated WebP..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

process_gif() {
    local file="$1"
    local size="$2"
    
    local dir_path
    local base_name
    local name_no_ext
    dir_path="$(dirname "$file")"
    base_name="$(basename "$file")"
    name_no_ext="${base_name%.*}"
    
    local thumb_dir="$dir_path/thumbnails"
    local output="$thumb_dir/${name_no_ext}.webp"
    
    # Skip if exists
    if [ -f "$output" ]; then
        echo "SKIP: $base_name"
        return 0
    fi
    
    mkdir -p "$thumb_dir"
    
    # Resize GIF and convert to WebP
    local temp_gif="/tmp/temp_thumb_$$.gif"
    
    if ffmpeg -i "$file" -vf "scale=${size}:${size}:force_original_aspect_ratio=decrease,pad=${size}:${size}:(ow-iw)/2:(oh-ih)/2" \
        -y "$temp_gif" -loglevel error 2>/dev/null; then
        
        if gif2webp -q 70 -m 4 "$temp_gif" -o "$output" 2>/dev/null; then
            echo "✓ $base_name"
        else
            echo "✗ $base_name (webp failed)"
        fi
        rm -f "$temp_gif"
    else
        echo "✗ $base_name (resize failed)"
    fi
}
export -f process_gif

# Count existing thumbnails for GIFs
GIF_EXISTING=$(find . -type f -iname "*.gif" ! -path "*/thumbnails/*" 2>/dev/null | while read f; do
    dir=$(dirname "$f")
    name=$(basename "${f%.*}")
    [ -f "$dir/thumbnails/${name}.webp" ] && echo "1"
done | wc -l)
GIF_TODO=$((GIF_COUNT - GIF_EXISTING))
echo "   Already done: $GIF_EXISTING, To process: $GIF_TODO"

if [ "$GIF_TODO" -gt 0 ]; then
    find . -type f -iname "*.gif" ! -path "*/thumbnails/*" -print0 2>/dev/null | \
        parallel -0 -j "$JOBS" --bar --eta process_gif {} "$SIZE"
else
    echo "   ✅ All GIFs already have thumbnails"
fi

# =============================================================================
# 4. PROCESS VIDEOS -> Static JPG Thumbnail (Parallel)
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎥 [3/3] Processing Videos..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

process_video() {
    local file="$1"
    local size="$2"
    
    local dir_path
    local base_name
    local name_no_ext
    dir_path="$(dirname "$file")"
    base_name="$(basename "$file")"
    name_no_ext="${base_name%.*}"
    
    local thumb_dir="$dir_path/thumbnails"
    local output="$thumb_dir/${name_no_ext}.jpg"
    
    # Skip if exists
    if [ -f "$output" ]; then
        echo "SKIP: $base_name"
        return 0
    fi
    
    mkdir -p "$thumb_dir"
    
    # Try to get frame at 5 seconds
    if ffmpeg -ss 00:00:05 -i "$file" -vframes 1 -q:v 2 \
        -vf "scale=${size}:${size}:force_original_aspect_ratio=increase,crop=${size}:${size}" \
        "$output" -y -loglevel error 2>/dev/null; then
        echo "✓ $base_name"
        return 0
    fi
    
    # Fallback: try at 1 second
    if ffmpeg -ss 00:00:01 -i "$file" -vframes 1 -q:v 2 \
        -vf "scale=${size}:${size}:force_original_aspect_ratio=increase,crop=${size}:${size}" \
        "$output" -y -loglevel error 2>/dev/null; then
        echo "✓ $base_name (1s)"
        return 0
    fi
    
    # Fallback: first frame
    if ffmpeg -i "$file" -vframes 1 -q:v 2 \
        -vf "scale=${size}:${size}:force_original_aspect_ratio=increase,crop=${size}:${size}" \
        "$output" -y -loglevel error 2>/dev/null; then
        echo "✓ $base_name (0s)"
    else
        echo "✗ $base_name (failed)"
    fi
}
export -f process_video

# Count existing thumbnails for videos
VID_EXISTING=$(find . -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) ! -path "*/thumbnails/*" 2>/dev/null | while read f; do
    dir=$(dirname "$f")
    name=$(basename "${f%.*}")
    [ -f "$dir/thumbnails/${name}.jpg" ] && echo "1"
done | wc -l)
VID_TODO=$((VID_COUNT - VID_EXISTING))
echo "   Already done: $VID_EXISTING, To process: $VID_TODO"

if [ "$VID_TODO" -gt 0 ]; then
    find . -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \) ! -path "*/thumbnails/*" -print0 2>/dev/null | \
        parallel -0 -j "$JOBS" --bar --eta process_video {} "$SIZE"
else
    echo "   ✅ All videos already have thumbnails"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "✅ COMPLETE!"
echo "=============================================="
THUMB_COUNT=$(find . -path "*/thumbnails/*" -type f \( -iname "*.jpg" -o -iname "*.webp" \) 2>/dev/null | wc -l)
echo "📊 Total thumbnails: $THUMB_COUNT"
echo "📁 Location: Each folder has its own 'thumbnails' subfolder"
echo "=============================================="
