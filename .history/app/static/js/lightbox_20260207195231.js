/**
 * lightbox.js - Lightbox functionality
 */

let currentImageIndex = 0;
let allImages = [];
let slideshowInterval = null;
let slideshowDelay = 1000;

/**
 * Load all images from grid for navigation
 */
function loadAllImages() {
    allImages = Array.from(document.querySelectorAll('.grid-item')).map((item, index) => ({
        folder: item.dataset.folder,
        filename: item.dataset.filename,
        isVideo: item.dataset.isVideo === 'true',
        index: index
    }));
}

/**
 * Open lightbox with image/video
 */
function openLightbox(imgElement) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxVideo = document.getElementById('lightboxVideo');
    const fullscreenBtn = document.getElementById('lightboxFullscreenBtn');

    const gridItem = imgElement.closest('.grid-item');
    const filename = gridItem.dataset.filename;
    const isVideo = gridItem.dataset.isVideo === 'true';
    const index = Array.from(document.querySelectorAll('.grid-item')).indexOf(gridItem);

    currentImageIndex = index;

    if (isVideo) {
        lightboxImage.style.display = 'none';
        lightboxVideo.style.display = 'block';
        lightboxVideo.querySelector('source').src = imgElement.querySelector('source').src;
        lightboxVideo.load();
        lightboxVideo.loop = true;
        lightboxVideo.muted = true;
        lightboxVideo.play().catch(() => { });
    } else {
        lightboxVideo.style.display = 'none';
        lightboxImage.style.display = 'block';
        lightboxImage.src = imgElement.dataset.fullSrc || imgElement.src;
        lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
    }

    // Handle fullscreen button visibility for mobile
    const isIPhone = /iPhone/i.test(navigator.userAgent);
    if (fullscreenBtn) {
        fullscreenBtn.style.display = isIPhone ? 'none' : 'flex';
    }

    lightbox.classList.add('active');
    updateLightboxFavorite();
    updateLightboxCounter();
    document.body.style.overflow = 'hidden';
}

/**
 * Close lightbox
 */
function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxVideo = document.getElementById('lightboxVideo');

    // Stop slideshow
    if (slideshowInterval) {
        clearInterval(slideshowInterval);
        slideshowInterval = null;
        const slideshowBtn = document.getElementById('lightboxSlideshowBtn');
        if (slideshowBtn) slideshowBtn.classList.remove('playing');
    }

    // Pause video
    if (lightboxVideo) {
        lightboxVideo.pause();
        lightboxVideo.currentTime = 0;
    }

    lightbox.classList.remove('active');
    document.body.style.overflow = '';
}

/**
 * Navigate to previous image
 */
function prevImage() {
    if (allImages.length === 0) loadAllImages();
    currentImageIndex = (currentImageIndex - 1 + allImages.length) % allImages.length;
    loadImageToLightbox();
}

/**
 * Navigate to next image
 */
function nextImage() {
    if (allImages.length === 0) loadAllImages();
    currentImageIndex = (currentImageIndex + 1) % allImages.length;
    loadImageToLightbox();
}

/**
 * Load current image to lightbox
 */
function loadImageToLightbox() {
    const gridItems = document.querySelectorAll('.grid-item');
    if (currentImageIndex < 0 || currentImageIndex >= gridItems.length) return;

    const gridItem = gridItems[currentImageIndex];
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxVideo = document.getElementById('lightboxVideo');
    const isVideo = gridItem.dataset.isVideo === 'true';

    if (isVideo) {
        lightboxImage.style.display = 'none';
        lightboxVideo.style.display = 'block';
        const video = gridItem.querySelector('video');
        if (video) {
            lightboxVideo.querySelector('source').src = video.querySelector('source').src;
            lightboxVideo.load();
            lightboxVideo.loop = true;
            lightboxVideo.muted = true;
            lightboxVideo.play().catch(() => { });
        }
    } else {
        lightboxVideo.style.display = 'none';
        lightboxVideo.pause();
        lightboxImage.style.display = 'block';
        const img = gridItem.querySelector('img');
        if (img) {
            lightboxImage.src = img.dataset.fullSrc || img.src;
            lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
        }
    }

    updateLightboxFavorite();
    updateLightboxCounter();
}

/**
 * Update lightbox counter display
 */
function updateLightboxCounter() {
    const counter = document.getElementById('lightboxCounter');
    if (counter) {
        counter.textContent = `${currentImageIndex + 1} / ${allImages.length || document.querySelectorAll('.grid-item').length}`;
    }
}

/**
 * Update lightbox favorite button state
 */
function updateLightboxFavorite() {
    const gridItems = document.querySelectorAll('.grid-item');
    const currentItem = gridItems[currentImageIndex];
    const lightboxFavBtn = document.getElementById('lightboxFavoriteBtn');

    if (!currentItem || !lightboxFavBtn) return;

    const heartBtn = currentItem.querySelector('.heart-btn');
    if (heartBtn && heartBtn.classList.contains('active')) {
        lightboxFavBtn.classList.add('active');
        lightboxFavBtn.textContent = '♥';
    } else {
        lightboxFavBtn.classList.remove('active');
        lightboxFavBtn.textContent = '♡';
    }
}

/**
 * Toggle favorite from lightbox
 */
function toggleLightboxFavorite() {
    const gridItems = document.querySelectorAll('.grid-item');
    const currentItem = gridItems[currentImageIndex];
    if (!currentItem) return;

    const folder = currentItem.dataset.folder;
    const filename = currentItem.dataset.filename;
    const heartBtn = currentItem.querySelector('.heart-btn');

    if (heartBtn) {
        toggleImageFavorite(folder, filename, heartBtn);
        setTimeout(updateLightboxFavorite, 100);
    }
}

/**
 * Delete image from lightbox
 */
function deleteLightboxImage() {
    const gridItems = document.querySelectorAll('.grid-item');
    const currentItem = gridItems[currentImageIndex];
    if (!currentItem) return;

    const folder = currentItem.dataset.folder;
    const filename = currentItem.dataset.filename;

    if (!confirm(`Delete ${filename}?`)) return;

    fetch(buildApiUrl('/api/image', folder, filename), { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                currentItem.remove();
                loadAllImages();

                if (allImages.length === 0) {
                    closeLightbox();
                } else {
                    currentImageIndex = Math.min(currentImageIndex, allImages.length - 1);
                    loadImageToLightbox();
                }
                showNotification('Image deleted', 'success');
            }
        })
        .catch(err => {
            console.error('Error deleting image:', err);
            showNotification('Error deleting image', 'error');
        });
}

/**
 * Toggle slideshow
 */
function toggleSlideshow() {
    const slideshowBtn = document.getElementById('lightboxSlideshowBtn');

    if (slideshowInterval) {
        clearInterval(slideshowInterval);
        slideshowInterval = null;
        if (slideshowBtn) slideshowBtn.classList.remove('playing');
    } else {
        slideshowInterval = setInterval(nextImage, slideshowDelay);
        if (slideshowBtn) slideshowBtn.classList.add('playing');
    }
}

/**
 * Toggle fullscreen
 */
function toggleFullscreen() {
    const lightboxContainer = document.querySelector('.lightbox-container');
    const isFullscreen = document.fullscreenElement || document.webkitFullscreenElement;

    if (isFullscreen) {
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    } else {
        if (lightboxContainer.requestFullscreen) lightboxContainer.requestFullscreen();
        else if (lightboxContainer.webkitRequestFullscreen) lightboxContainer.webkitRequestFullscreen();
    }
}

/**
 * Zoom image
 */
function zoomImage(direction) {
    const lightboxImage = document.getElementById('lightboxImage');
    if (!lightboxImage || lightboxImage.style.display === 'none') return;

    const currentTransform = lightboxImage.style.transform || 'scale(1)';
    const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
    let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;

    if (direction === 'in') {
        currentScale = Math.min(currentScale * 1.2, 5);
    } else {
        currentScale = Math.max(currentScale / 1.2, 0.5);
    }

    lightboxImage.style.transform = `scale(${currentScale})`;
    lightboxImage.style.cursor = currentScale > 1 ? 'grab' : '';
}

// ============================================================================
// KEYBOARD NAVIGATION
// ============================================================================

document.addEventListener('keydown', (e) => {
    const lightbox = document.getElementById('lightbox');
    const isInLightbox = lightbox && lightbox.classList.contains('active');
    const isFullscreen = document.fullscreenElement || document.webkitFullscreenElement;

    if (isInLightbox || isFullscreen) {
        switch (e.key) {
            case 'Escape':
                if (isFullscreen) {
                    document.exitFullscreen?.() || document.webkitExitFullscreen?.();
                } else {
                    closeLightbox();
                }
                break;
            case 'ArrowLeft':
                prevImage();
                break;
            case 'ArrowRight':
                nextImage();
                break;
            case ' ':
            case 'Spacebar':
                e.preventDefault();
                toggleSlideshow();
                break;
            case '+':
            case '=':
                e.preventDefault();
                zoomImage('in');
                break;
            case '-':
            case '_':
                e.preventDefault();
                zoomImage('out');
                break;
            case '0':
                e.preventDefault();
                const img = document.getElementById('lightboxImage');
                if (img) img.style.transform = 'scale(1)';
                break;
            case 'Delete':
            case 'Backspace':
                e.preventDefault();
                deleteLightboxImage();
                break;
        }
    }
});

// Wheel navigation in lightbox
document.addEventListener('wheel', (e) => {
    const lightbox = document.getElementById('lightbox');
    const isInLightbox = lightbox && lightbox.classList.contains('active');

    if (isInLightbox) {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            zoomImage(e.deltaY < 0 ? 'in' : 'out');
        } else if (Math.abs(e.deltaY) > 5) {
            e.deltaY > 0 ? nextImage() : prevImage();
        }
    }
}, { passive: false });

// Close lightbox when clicking outside
document.addEventListener('click', (e) => {
    const lightbox = document.getElementById('lightbox');
    if (lightbox && e.target === lightbox) {
        closeLightbox();
    }
});

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', loadAllImages);
