#!/bin/bash
#
# Fast thumbnail generator using ffmpeg and ImageMagick
# Much faster than Python for video and image processing
#
# Usage:
#   ./generate_thumbnails.sh
#   ./generate_thumbnails.sh --size 400
#   ./generate_thumbnails.sh --folder "corba"
#   ./generate_thumbnails.sh --clean
#   ./generate_thumbnails.sh --jobs 8
#

set -e

# Configuration
DATASET_PATH="${DATASET_PATH:-./dataset}"
THUMB_SIZE=300
JOBS=4
CLEAN=false
TARGET_FOLDER=""
VIDEO_PREVIEW_DURATION=3
VIDEO_PREVIEW_FPS=8

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --size|-s)
            THUMB_SIZE="$2"
            shift 2
            ;;
        --folder|-f)
            TARGET_FOLDER="$2"
            shift 2
            ;;
        --jobs|-j)
            JOBS="$2"
            shift 2
            ;;
        --clean|-c)
            CLEAN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --size, -s SIZE      Thumbnail size (default: 300)"
            echo "  --folder, -f FOLDER  Process specific folder only"
            echo "  --jobs, -j JOBS      Parallel jobs (default: 4)"
            echo "  --clean, -c          Remove old thumbnails first"
            echo "  --help, -h           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check dependencies
check_deps() {
    local missing=()
    
    if ! command -v ffmpeg &> /dev/null; then
        missing+=("ffmpeg")
    fi
    
    if ! command -v convert &> /dev/null; then
        missing+=("imagemagick")
    fi
    
    if ! command -v parallel &> /dev/null; then
        echo -e "${YELLOW}⚠️  GNU parallel not found. Install for faster processing:${NC}"
        echo "   brew install parallel  (macOS)"
        echo "   apt install parallel   (Linux)"
        echo ""
        JOBS=1
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing dependencies: ${missing[*]}${NC}"
        echo ""
        echo "Install on macOS:"
        echo "   brew install ffmpeg imagemagick"
        echo ""
        echo "Install on Linux:"
        echo "   apt install ffmpeg imagemagick"
        exit 1
    fi
}

# Generate thumbnail for a single image
generate_image_thumb() {
    local src="$1"
    local thumb_dir="$2"
    local size="$3"
    local filename=$(basename "$src")
    local name="${filename%.*}"
    local ext="${filename##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    
    # Check if animated GIF or WebP
    local is_animated=false
    if [[ "$ext" == "gif" ]]; then
        local frames=$(identify -format "%n" "$src" 2>/dev/null | head -1 || echo "1")
        # Remove any non-numeric characters
        frames=$(echo "$frames" | tr -cd '0-9')
        frames=${frames:-1}
        if [[ "$frames" -gt 1 ]] 2>/dev/null; then
            is_animated=true
        fi
    elif [[ "$ext" == "webp" ]]; then
        if webpmux -info "$src" 2>/dev/null | grep -q "animation"; then
            is_animated=true
        fi
    fi
    
    if $is_animated; then
        # Animated → animated WebP thumbnail
        local thumb_path="${thumb_dir}/${name}_thumb.webp"
        
        # Skip if up-to-date
        if [[ -f "$thumb_path" && "$thumb_path" -nt "$src" ]]; then
            echo "SKIP:$filename"
            return
        fi
        
        # Use ffmpeg for animated conversion (faster than ImageMagick)
        ffmpeg -y -i "$src" \
            -vf "scale=${size}:${size}:force_original_aspect_ratio=decrease" \
            -loop 0 -an \
            "$thumb_path" 2>/dev/null && echo "OK:$filename" || echo "FAIL:$filename"
    else
        # Static image → JPEG thumbnail
        local thumb_path="${thumb_dir}/${name}_thumb.jpg"
        
        # Skip if up-to-date
        if [[ -f "$thumb_path" && "$thumb_path" -nt "$src" ]]; then
            echo "SKIP:$filename"
            return
        fi
        
        # Use ImageMagick convert (fast for static images)
        convert "$src[0]" \
            -thumbnail "${size}x${size}>" \
            -quality 85 \
            "$thumb_path" 2>/dev/null && echo "OK:$filename" || echo "FAIL:$filename"
    fi
}

# Generate thumbnail for a video
generate_video_thumb() {
    local src="$1"
    local thumb_dir="$2"
    local size="$3"
    local filename=$(basename "$src")
    local name="${filename%.*}"
    local thumb_path="${thumb_dir}/${name}_thumb.webp"
    
    # Skip if up-to-date
    if [[ -f "$thumb_path" && "$thumb_path" -nt "$src" ]]; then
        echo "SKIP:$filename"
        return
    fi
    
    # Get video duration
    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$src" 2>/dev/null)
    duration=${duration%.*}  # Remove decimal
    duration=${duration:-0}
    
    if [[ "$duration" -lt 1 ]]; then
        # Very short video - just get first frame as static
        local static_thumb="${thumb_dir}/${name}_thumb.jpg"
        ffmpeg -y -i "$src" -vframes 1 \
            -vf "scale='min(${size},iw)':min'(${size},ih)':force_original_aspect_ratio=decrease" \
            "$static_thumb" 2>/dev/null && echo "OK:$filename" || echo "FAIL:$filename"
    else
        # Create animated preview from first few seconds
        local preview_duration=$VIDEO_PREVIEW_DURATION
        if [[ "$duration" -lt "$preview_duration" ]]; then
            preview_duration=$duration
        fi
        
        # Generate animated WebP preview
        ffmpeg -y -i "$src" \
            -t "$preview_duration" \
            -vf "scale='min(${size},iw)':min'(${size},ih)':force_original_aspect_ratio=decrease,fps=${VIDEO_PREVIEW_FPS}" \
            -loop 0 -an \
            -quality 75 \
            "$thumb_path" 2>/dev/null && echo "OK:$filename" || echo "FAIL:$filename"
    fi
}

# Export functions for parallel
export -f generate_image_thumb
export -f generate_video_thumb

# Process a single file (dispatcher)
process_file() {
    local src="$1"
    local thumb_dir="$2"
    local size="$3"
    local filename=$(basename "$src")
    local ext="${filename##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    
    case "$ext" in
        jpg|jpeg|png|gif|webp|bmp|heic)
            generate_image_thumb "$src" "$thumb_dir" "$size"
            ;;
        mp4|mov|avi|webm|mkv)
            generate_video_thumb "$src" "$thumb_dir" "$size"
            ;;
        *)
            echo "SKIP:$filename (unsupported)"
            ;;
    esac
}

export -f process_file

# Main
main() {
    echo -e "${BLUE}🖼️  Fast Thumbnail Generator${NC}"
    echo "=================================================="
    echo -e "📁 Dataset: ${DATASET_PATH}"
    echo -e "📐 Size: ${THUMB_SIZE}x${THUMB_SIZE}"
    echo -e "👷 Jobs: ${JOBS}"
    echo -e "🧹 Clean: ${CLEAN}"
    echo "=================================================="
    
    check_deps
    
    # Determine folders to process
    local folders=()
    if [[ -n "$TARGET_FOLDER" ]]; then
        folders+=("${DATASET_PATH}/${TARGET_FOLDER}")
    else
        # Find all folders with media files
        while IFS= read -r -d '' folder; do
            folders+=("$folder")
        done < <(find "$DATASET_PATH" -type d ! -name ".*" ! -path "*/.thumbnails*" -print0)
    fi
    
    # Count total files
    local total_files=0
    for folder in "${folders[@]}"; do
        local count=$(find "$folder" -maxdepth 1 -type f \( \
            -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \
            -o -iname "*.webp" -o -iname "*.bmp" -o -iname "*.heic" \
            -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.webm" \
        \) 2>/dev/null | wc -l)
        total_files=$((total_files + count))
    done
    
    echo -e "\n📊 Total files to process: ${total_files}"
    echo ""
    
    local total_ok=0
    local total_skip=0
    local total_fail=0
    local processed=0
    local start_time=$(date +%s)
    
    for folder in "${folders[@]}"; do
        [[ ! -d "$folder" ]] && continue
        
        local rel_path="${folder#$DATASET_PATH/}"
        local thumb_dir="${folder}/.thumbnails"
        
        # Clean old thumbnails if requested
        if $CLEAN && [[ -d "$thumb_dir" ]]; then
            rm -rf "$thumb_dir"
        fi
        
        mkdir -p "$thumb_dir"
        
        # Find media files in this folder
        local files=()
        while IFS= read -r -d '' file; do
            files+=("$file")
        done < <(find "$folder" -maxdepth 1 -type f \( \
            -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \
            -o -iname "*.webp" -o -iname "*.bmp" -o -iname "*.heic" \
            -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.webm" \
        \) -print0 2>/dev/null)
        
        [[ ${#files[@]} -eq 0 ]] && continue
        
        echo -e "${BLUE}📁 Processing: ${rel_path} (${#files[@]} files)${NC}"
        
        local folder_ok=0
        local folder_skip=0
        local folder_fail=0
        
        if command -v parallel &> /dev/null && [[ $JOBS -gt 1 ]]; then
            # Use GNU parallel for speed
            while IFS= read -r result; do
                processed=$((processed + 1))
                local status="${result%%:*}"
                local fname="${result#*:}"
                
                case "$status" in
                    OK)
                        folder_ok=$((folder_ok + 1))
                        echo -e "    [${processed}/${total_files}] ${GREEN}✅${NC} ${fname}"
                        ;;
                    SKIP)
                        folder_skip=$((folder_skip + 1))
                        ;;
                    FAIL)
                        folder_fail=$((folder_fail + 1))
                        echo -e "    [${processed}/${total_files}] ${RED}❌${NC} ${fname}"
                        ;;
                esac
            done < <(printf '%s\n' "${files[@]}" | parallel -j "$JOBS" process_file {} "$thumb_dir" "$THUMB_SIZE")
        else
            # Sequential processing
            for file in "${files[@]}"; do
                processed=$((processed + 1))
                local result=$(process_file "$file" "$thumb_dir" "$THUMB_SIZE")
                local status="${result%%:*}"
                local fname="${result#*:}"
                
                case "$status" in
                    OK)
                        folder_ok=$((folder_ok + 1))
                        echo -e "    [${processed}/${total_files}] ${GREEN}✅${NC} ${fname}"
                        ;;
                    SKIP)
                        folder_skip=$((folder_skip + 1))
                        ;;
                    FAIL)
                        folder_fail=$((folder_fail + 1))
                        echo -e "    [${processed}/${total_files}] ${RED}❌${NC} ${fname}"
                        ;;
                esac
            done
        fi
        
        total_ok=$((total_ok + folder_ok))
        total_skip=$((total_skip + folder_skip))
        total_fail=$((total_fail + folder_fail))
        
        echo -e "    📊 Folder done: ${GREEN}✅ ${folder_ok}${NC} created | ⏭️ ${folder_skip} skipped | ${RED}❌ ${folder_fail}${NC} failed"
        
        local progress=$((processed * 100 / total_files))
        echo -e "    📈 Overall progress: ${processed}/${total_files} (${progress}%)"
    done
    
    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    
    echo ""
    echo "=================================================="
    echo -e "${GREEN}📊 Summary${NC}"
    echo "=================================================="
    echo -e "${GREEN}✅ Thumbnails created: ${total_ok}${NC}"
    echo -e "⏭️  Already existed: ${total_skip}"
    echo -e "${RED}❌ Failed: ${total_fail}${NC}"
    echo -e "⏱️  Time: ${elapsed} seconds"
    
    if [[ $total_ok -gt 0 && $elapsed -gt 0 ]]; then
        local speed=$((total_ok / elapsed))
        echo -e "⚡ Speed: ~${speed} thumbnails/second"
    fi
    
    echo ""
    echo -e "${GREEN}✨ Done!${NC}"
}

main "$@"
