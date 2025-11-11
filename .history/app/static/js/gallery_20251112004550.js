// Gallery functionality with tags and justified layout
let currentImageIndex = 0;
let allImages = [];
let currentFolderName = '';
let favoriteImages = new Set();

document.addEventListener('DOMContentLoaded', () => {
    currentFolderName = document.querySelector('.breadcrumb-item strong')?.textContent || '';

    // Load all images
    loadAllImages();

    // Setup event listeners
    setupEventListeners();

    // Close tag modal when clicking outside
    const tagModal = document.getElementById('tagModal');
    if (tagModal) {
        tagModal.addEventListener('click', (e) => {
            if (e.target === tagModal) {
                closeTagModal();
            }
        });
    }

    // Close button in tag modal
    const closeModalBtn = document.querySelector('.modal-close');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeTagModal);
    }

    // Close lightbox when clicking outside
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) {
                closeLightbox();
            }
        });
    }

    // Setup favorite button in lightbox
    const lightboxFavBtn = document.querySelector('.lightbox-favorite');
    if (lightboxFavBtn) {
        lightboxFavBtn.addEventListener('click', () => {
            const images = document.querySelectorAll('.grid-item');
            const currentImage = images[currentImageIndex];
            if (currentImage) {
                const folderName = currentImage.dataset.folder;
                const filename = currentImage.dataset.filename;
                toggleImageFavorite(folderName, filename);
            }
        });
    }
});

function loadAllImages() {
    // Get images from grid
    allImages = Array.from(document.querySelectorAll('.grid-item')).map((item, index) => ({
        folder: item.dataset.folder,
        filename: item.dataset.filename,
        index: index
    }));

    /* ---------------- Reels / Vertical feed (mobile) ---------------- */
    // Initialize Reels mode automatically on touch devices when folder has videos
    function initReelsModeIfNeeded() {
        const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
        const videos = document.querySelectorAll('.gallery-video');
        if (isTouch && videos.length > 0) {
            enableReelsMode();
        }
    }

    function enableReelsMode() {
        const container = document.getElementById('galleryContainer');
        if (!container) return;
        document.body.classList.add('reels-view');

        // Make imagesGrid scrollable full-page vertical feed
        const grid = document.getElementById('imagesGrid');
        if (!grid) return;

        // Ensure each grid-item fills viewport
        grid.querySelectorAll('.grid-item').forEach(item => {
            item.style.width = '100%';
            item.style.height = '100vh';
        });

        setupReelsAutoplay();
        setupReelsTouchNavigation(grid);
    }

    function setupReelsAutoplay() {
        const options = {
            root: null,
            rootMargin: '0px',
            threshold: [0.5]
        };

        const callback = (entries) => {
            entries.forEach(entry => {
                const video = entry.target.querySelector('video');
                if (!video) return;

                if (entry.intersectionRatio >= 0.5) {
                    // Play and ensure muted/playsinline for mobile autoplay
                    video.muted = true;
                    video.playsInline = true;
                    const playPromise = video.play();
                    if (playPromise && typeof playPromise.then === 'function') {
                        playPromise.catch(() => {
                            // Autoplay blocked: show overlay play icon (already present)
                        });
                    }
                } else {
                    video.pause();
                }
            });
        };

        const observer = new IntersectionObserver(callback, options);
        document.querySelectorAll('.grid-item').forEach(item => observer.observe(item));
    }

    function setupReelsTouchNavigation(grid) {
        let startY = 0;
        let endY = 0;

        grid.addEventListener('touchstart', (e) => {
            if (e.touches && e.touches.length > 0) startY = e.touches[0].clientY;
        }, { passive: true });

        grid.addEventListener('touchend', (e) => {
            endY = (e.changedTouches && e.changedTouches.length > 0) ? e.changedTouches[0].clientY : 0;
            const delta = startY - endY;
            const threshold = 50; // minimal swipe distance
            if (Math.abs(delta) > threshold) {
                // Swipe up -> next, Swipe down -> prev
                if (delta > 0) {
                    scrollToNext(grid);
                } else {
                    scrollToPrev(grid);
                }
            }
        }, { passive: true });
    }

    function scrollToNext(grid) {
        const scrollTop = grid.scrollTop;
        const vh = window.innerHeight;
        grid.scrollTo({ top: scrollTop + vh, behavior: 'smooth' });
    }

    function scrollToPrev(grid) {
        const scrollTop = grid.scrollTop;
        const vh = window.innerHeight;
        grid.scrollTo({ top: Math.max(0, scrollTop - vh), behavior: 'smooth' });
    }

    // Run reels init after DOM content to check for touch devices
    document.addEventListener('DOMContentLoaded', () => {
        // Slight delay to allow lazy elements to be inserted
        setTimeout(initReelsModeIfNeeded, 300);
    });

    /* ---------------- Lightbox video playback/loop fixes ---------------- */
    // Ensure lightbox plays videos and respects loop; fallback to replay on 'ended'
    const originalOpenLightbox = window.openLightbox;
    if (typeof originalOpenLightbox === 'function') {
        window.openLightbox = function (imgElement) {
            originalOpenLightbox(imgElement);

            // If the lightbox contains a video, try to play it and ensure loop is set
            const lightboxVideo = document.getElementById('lightboxVideo');
            if (lightboxVideo && lightboxVideo.style.display !== 'none') {
                lightboxVideo.loop = true;
                lightboxVideo.muted = true; // allow autoplay on mobile
                lightboxVideo.playsInline = true;

                // Try play (user clicked to open so should be allowed)
                const playPromise = lightboxVideo.play();
                if (playPromise && typeof playPromise.then === 'function') {
                    playPromise.catch(() => {
                        // If play is blocked, don't crash — user can use controls
                    });
                }

                // Fallback: if loop isn't honored, restart on ended
                lightboxVideo.removeEventListener('ended', lightboxVideo._replayHandler);
                lightboxVideo._replayHandler = () => {
                    try { lightboxVideo.currentTime = 0; lightboxVideo.play(); } catch (e) { }
                };
                lightboxVideo.addEventListener('ended', lightboxVideo._replayHandler);
            }
        };
    }

    // Also ensure loadImageToLightbox plays video when navigating
    const originalLoadImageToLightbox = window.loadImageToLightbox;
    if (typeof originalLoadImageToLightbox === 'function') {
        window.loadImageToLightbox = function (gridItem) {
            originalLoadImageToLightbox(gridItem);

            const lightboxVideo = document.getElementById('lightboxVideo');
            if (lightboxVideo && lightboxVideo.style.display !== 'none') {
                lightboxVideo.loop = true;
                lightboxVideo.muted = true;
                lightboxVideo.playsInline = true;
                const p = lightboxVideo.play();
                if (p && typeof p.then === 'function') p.catch(() => { });
            }
        };
    }
}

function setupEventListeners() {
    // Close lightbox on escape key
    document.addEventListener('keydown', (e) => {
        const lightbox = document.getElementById('lightbox');
        if (lightbox && lightbox.classList.contains('active')) {
            if (e.key === 'Escape') {
                closeLightbox();
            } else if (e.key === 'ArrowLeft') {
                prevImage();
            } else if (e.key === 'ArrowRight') {
                nextImage();
            } else if (e.key === '+' || e.key === '=') {
                // Zoom in with + or = key
                e.preventDefault();
                zoomImage('in');
            } else if (e.key === '-' || e.key === '_') {
                // Zoom out with - key
                e.preventDefault();
                zoomImage('out');
            } else if (e.key === '0') {
                // Reset zoom with 0 key
                e.preventDefault();
                const lightboxImage = document.getElementById('lightboxImage');
                if (lightboxImage) {
                    lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
                    lightboxImage.style.cursor = '';
                }
            }
        }

        // Ctrl+Wheel for zoom
        if (e.key === 'Control' || e.key === 'Meta') {
            // Will be handled by wheel event
        }
    });

    // Wheel navigation and zoom in lightbox
    document.addEventListener('wheel', (e) => {
        const lightbox = document.getElementById('lightbox');
        if (!lightbox || !lightbox.classList.contains('active')) return;

        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const lightboxImage = document.getElementById('lightboxImage');
            const rect = lightboxImage.getBoundingClientRect();

            // Calculate mouse position relative to image
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            zoomImageAtPoint(e.deltaY < 0 ? 'in' : 'out', mouseX, mouseY, rect.width, rect.height);
        } else {
            // Wheel to navigate (but add threshold to avoid accidental navigation)
            if (Math.abs(e.deltaY) > 5) {
                if (e.deltaY > 0) {
                    nextImage();
                } else {
                    prevImage();
                }
            }
        }
    }, { passive: false });

    // Favorite button
    const favoriteBtn = document.getElementById('favoriteBtn');
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', toggleFavorite);
    }
}

function openLightbox(imgElement) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxVideo = document.getElementById('lightboxVideo');

    // Get filename from the grid item
    const gridItem = imgElement.closest('.grid-item');
    const filename = gridItem.dataset.filename;
    const isVideo = gridItem.dataset.isVideo === 'true';
    const index = Array.from(document.querySelectorAll('.grid-item')).indexOf(gridItem);

    currentImageIndex = index;

    // Show either video or image
    if (isVideo) {
        lightboxImage.style.display = 'none';
        lightboxVideo.style.display = 'block';
        lightboxVideo.querySelector('source').src = imgElement.querySelector('source').src;
        lightboxVideo.load();
    } else {
        lightboxVideo.style.display = 'none';
        lightboxImage.style.display = 'block';
        lightboxImage.src = imgElement.src;
        lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
        lightboxImage.style.cursor = '';
    }

    lightbox.classList.add('active');

    updateLightboxFavorite();
    updateLightboxCounter();
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxVideo = document.getElementById('lightboxVideo');

    // Pause video if playing
    if (lightboxVideo) {
        lightboxVideo.pause();
    }

    lightbox.classList.remove('active');
    document.body.style.overflow = 'auto';
}

function toggleFullscreen() {
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxVideo = document.getElementById('lightboxVideo');
    const activeElement = lightboxImage.style.display !== 'none' ? lightboxImage : lightboxVideo;

    // Toggle the fullscreen class
    activeElement.classList.toggle('fullscreen-mode');

    // Update button icon
    const btn = document.getElementById('lightboxFullscreenBtn');
    if (activeElement.classList.contains('fullscreen-mode')) {
        btn.textContent = '⛶'; // Exit fullscreen icon
        btn.title = 'Exit fullscreen';
    } else {
        btn.textContent = '⛶'; // Fullscreen icon
        btn.title = 'Toggle fullscreen';
    }
}

/* Lightbox touch navigation: horizontal for images, vertical for videos */
function setupLightboxTouchNavigation() {
    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    let startX = 0;
    let startY = 0;
    let isTouching = false;

    lightbox.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 0) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isTouching = true;
        }
    }, { passive: true });

    lightbox.addEventListener('touchend', (e) => {
        if (!isTouching) return;
        isTouching = false;

        const endX = (e.changedTouches && e.changedTouches.length > 0) ? e.changedTouches[0].clientX : startX;
        const endY = (e.changedTouches && e.changedTouches.length > 0) ? e.changedTouches[0].clientY : startY;

        const deltaX = startX - endX;
        const deltaY = startY - endY;

        const lightboxImage = document.getElementById('lightboxImage');
        const lightboxVideo = document.getElementById('lightboxVideo');
        const isVideo = lightboxVideo && lightboxVideo.style.display !== 'none';

        const absX = Math.abs(deltaX);
        const absY = Math.abs(deltaY);

        // thresholds
        const horizThreshold = 50; // px
        const vertThreshold = 50; // px

        if (isVideo) {
            // vertical navigation for videos
            if (deltaY > vertThreshold) {
                // swipe up -> next video
                nextImage();
            } else if (deltaY < -vertThreshold) {
                // swipe down -> previous video
                prevImage();
            }
        } else {
            // horizontal navigation for images
            if (deltaX > horizThreshold && absX > absY) {
                // swipe left -> next image
                nextImage();
            } else if (deltaX < -horizThreshold && absX > absY) {
                // swipe right -> previous image
                prevImage();
            }
        }
    }, { passive: true });
}

// Setup lightbox touch nav on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    setupLightboxTouchNavigation();
});

function nextImage() {
    const images = document.querySelectorAll('.grid-item');
    currentImageIndex = (currentImageIndex + 1) % images.length;
    loadImageToLightbox(images[currentImageIndex]);
}

function prevImage() {
    const images = document.querySelectorAll('.grid-item');
    currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
    loadImageToLightbox(images[currentImageIndex]);
}

function loadImageToLightbox(gridItem) {
    const img = gridItem.querySelector('.gallery-image');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxVideo = document.getElementById('lightboxVideo');
    const isVideo = gridItem.dataset.isVideo === 'true';

    // Pause any playing video
    if (lightboxVideo) {
        lightboxVideo.pause();
    }

    // Show either video or image
    if (isVideo) {
        lightboxImage.style.display = 'none';
        lightboxVideo.style.display = 'block';
        lightboxVideo.querySelector('source').src = img.querySelector('source').src;
        lightboxVideo.load();
    } else {
        lightboxVideo.style.display = 'none';
        lightboxImage.style.display = 'block';
        lightboxImage.src = img.src;
        lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
        lightboxImage.style.cursor = '';
    }

    updateLightboxCounter();
    updateLightboxFavorite();
}

function updateLightboxCounter() {
    const images = document.querySelectorAll('.grid-item');
    const counter = document.getElementById('lightboxCounter');
    counter.textContent = `${currentImageIndex + 1} / ${images.length}`;
}

function updateLightboxFavorite() {
    const images = document.querySelectorAll('.grid-item');
    const currentImage = images[currentImageIndex];
    if (!currentImage) return;

    const filename = currentImage.dataset.filename;
    const favoriteBtn = document.querySelector('.lightbox-favorite-btn');

    if (favoriteBtn) {
        if (favoriteImages.has(filename)) {
            favoriteBtn.classList.add('active');
        } else {
            favoriteBtn.classList.remove('active');
        }
    }
}

function zoomImage(direction) {
    const lightboxImage = document.getElementById('lightboxImage');
    const currentTransform = lightboxImage.style.transform || 'scale(1) translate(0px, 0px)';
    const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
    const translateMatch = currentTransform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/);

    const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
    const currentX = translateMatch ? parseFloat(translateMatch[1]) : 0;
    const currentY = translateMatch ? parseFloat(translateMatch[2]) : 0;

    let newScale = currentScale;
    // Increased max zoom from 3x to 6x
    if (direction === 'in') {
        newScale = Math.min(currentScale + 0.25, 6);
    } else {
        newScale = Math.max(currentScale - 0.25, 1);
    }

    // Reset translation when zooming back to 1x
    if (newScale === 1) {
        lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
    } else {
        lightboxImage.style.transform = `scale(${newScale}) translate(${currentX}px, ${currentY}px)`;
    }
}

function zoomImageAtPoint(direction, mouseX, mouseY, imgWidth, imgHeight) {
    const lightboxImage = document.getElementById('lightboxImage');
    const currentTransform = lightboxImage.style.transform || 'scale(1) translate(0px, 0px)';
    const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
    const translateMatch = currentTransform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/);

    const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
    const currentX = translateMatch ? parseFloat(translateMatch[1]) : 0;
    const currentY = translateMatch ? parseFloat(translateMatch[2]) : 0;

    // Calculate new scale - Increased max zoom from 3x to 6x
    let newScale = currentScale;
    // Use adaptive zoom step: smaller steps at higher zoom levels for finer control
    const zoomStep = currentScale < 2 ? 0.25 : 0.3;

    if (direction === 'in') {
        newScale = Math.min(currentScale + zoomStep, 6);
    } else {
        newScale = Math.max(currentScale - zoomStep, 1);
    }

    // Reset translation when zooming back to 1x
    if (newScale === 1) {
        lightboxImage.style.transform = 'scale(1) translate(0px, 0px)';
        lightboxImage.style.cursor = '';
    } else {
        // Calculate the point in the image that was under the mouse
        // This keeps that point under the mouse after zooming
        const scaleChange = newScale / currentScale;

        // Calculate mouse position relative to center
        const centerX = imgWidth / 2;
        const centerY = imgHeight / 2;
        const offsetX = mouseX - centerX;
        const offsetY = mouseY - centerY;

        // Adjust translation to keep the point under the mouse cursor
        const newX = currentX - (offsetX * (scaleChange - 1));
        const newY = currentY - (offsetY * (scaleChange - 1));

        lightboxImage.style.transform = `scale(${newScale}) translate(${newX}px, ${newY}px)`;
        lightboxImage.style.cursor = 'grab';
    }
}

// Pan/drag functionality for zoomed images with middle mouse button
let isPanning = false;
let startX = 0;
let startY = 0;
let currentTranslateX = 0;
let currentTranslateY = 0;

function setupImagePanning() {
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');

    if (!lightbox || !lightboxImage) return;

    // Start panning on middle mouse button down
    lightboxImage.addEventListener('mousedown', (e) => {
        // Middle mouse button (button === 1)
        if (e.button === 1) {
            e.preventDefault();

            const currentTransform = lightboxImage.style.transform || 'scale(1) translate(0px, 0px)';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;

            // Only allow panning when zoomed in
            if (currentScale > 1) {
                isPanning = true;
                startX = e.clientX;
                startY = e.clientY;

                const translateMatch = currentTransform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/);
                currentTranslateX = translateMatch ? parseFloat(translateMatch[1]) : 0;
                currentTranslateY = translateMatch ? parseFloat(translateMatch[2]) : 0;

                lightboxImage.style.cursor = 'grabbing';
            }
        }
    });

    // Pan/move the image
    lightboxImage.addEventListener('mousemove', (e) => {
        if (!isPanning) return;

        e.preventDefault();

        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;

        const newX = currentTranslateX + deltaX;
        const newY = currentTranslateY + deltaY;

        const currentTransform = lightboxImage.style.transform || 'scale(1) translate(0px, 0px)';
        const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
        const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;

        lightboxImage.style.transform = `scale(${currentScale}) translate(${newX}px, ${newY}px)`;
    });

    // Stop panning on mouse up
    const stopPanning = () => {
        if (isPanning) {
            isPanning = false;
            const lightboxImage = document.getElementById('lightboxImage');
            if (lightboxImage) {
                lightboxImage.style.cursor = '';
            }
        }
    };

    lightboxImage.addEventListener('mouseup', stopPanning);
    lightboxImage.addEventListener('mouseleave', stopPanning);
    document.addEventListener('mouseup', stopPanning);

    // Prevent context menu on middle mouse button
    lightboxImage.addEventListener('contextmenu', (e) => {
        if (e.button === 1) {
            e.preventDefault();
        }
    });

    // Change cursor when hovering over zoomed image
    lightboxImage.addEventListener('mouseover', () => {
        const currentTransform = lightboxImage.style.transform || 'scale(1) translate(0px, 0px)';
        const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
        const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;

        if (currentScale > 1 && !isPanning) {
            lightboxImage.style.cursor = 'grab';
        }
    });

    lightboxImage.addEventListener('mouseout', () => {
        if (!isPanning) {
            lightboxImage.style.cursor = '';
        }
    });
}

// Call setup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    setupImagePanning();
});

function deleteImage(folderName, filename, button) {
    if (!confirm(`Delete "${filename}"? This action cannot be undone.`)) return;

    fetch(`/api/image/${folderName}/${filename}`, {
        method: 'DELETE'
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Remove from DOM
                const gridItem = button.closest('.grid-item');
                gridItem.remove();

                // Update image list
                loadAllImages();

                // Show notification
                showNotification('Image deleted successfully', 'success');
            } else {
                showNotification(data.message || 'Error deleting image', 'error');
            }
        })
        .catch(err => {
            console.error('Error deleting image:', err);
            showNotification('Error deleting image', 'error');
        });
}

function toggleImageFavorite(folderName, filename, button) {
    // Check if already favorited
    const isCurrentlyFavorited = button && button.classList.contains('active');

    const method = isCurrentlyFavorited ? 'DELETE' : 'POST';

    fetch(`/api/favorite/${folderName}/${filename}`, {
        method: method
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Update button state
                if (button) {
                    if (isCurrentlyFavorited) {
                        button.classList.remove('active');
                        button.textContent = '♡';
                    } else {
                        button.classList.add('active');
                        button.textContent = '♥';
                    }
                }

                // Update lightbox button if open
                updateLightboxFavoriteButton();

                showNotification(
                    isCurrentlyFavorited ? 'Removed from favorites' : '❤️ Added to favorites',
                    'success'
                );
            } else {
                showNotification(data.message || 'Error updating favorite', 'error');
            }
        })
        .catch(err => {
            console.error('Error toggling favorite:', err);
            showNotification('Error updating favorite', 'error');
        });
}

function updateLightboxFavoriteButton() {
    const images = document.querySelectorAll('.grid-item');
    const currentImage = images[currentImageIndex];
    if (!currentImage) return;

    const folderName = currentImage.dataset.folder;
    const filename = currentImage.dataset.filename;
    const favoriteBtn = document.querySelector('.lightbox-favorite');

    if (!favoriteBtn) return;

    // Query the API to check if this image is favorited
    fetch(`/api/favorite/${folderName}/${filename}`)
        .then(r => r.json())
        .then(data => {
            if (data.is_favorite) {
                favoriteBtn.classList.add('active');
            } else {
                favoriteBtn.classList.remove('active');
            }
        })
        .catch(err => console.error('Error checking favorite status:', err));
}

function toggleLightboxFavorite() {
    const images = document.querySelectorAll('.grid-item');
    const currentImage = images[currentImageIndex];
    if (!currentImage) return;

    const folderName = currentImage.dataset.folder;
    const filename = currentImage.dataset.filename;

    toggleImageFavorite(folderName, filename);
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Tag management functions
function openTagModal(folderName, filename) {
    const modal = document.getElementById('tagModal');
    if (!modal) return;

    // Store current image info for tag operations
    modal.dataset.folder = folderName;
    modal.dataset.filename = filename;

    // Show modal
    modal.classList.add('active');

    // Load available tags and current image tags
    updateTagsList();
    loadImageTags(folderName, filename);
}

function closeTagModal() {
    const modal = document.getElementById('tagModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function updateTagsList() {
    const existingTags = document.getElementById('existingTags');
    if (!existingTags) return;

    fetch('/api/tags')
        .then(r => r.json())
        .then(tags => {
            if (tags.length === 0) {
                existingTags.innerHTML = '<p style="color: #999; font-size: 0.9em;">No tags yet. Create one below.</p>';
            } else {
                existingTags.innerHTML = tags
                    .map(tag => `
                        <label class="tag-checkbox" style="border-left: 4px solid ${tag.color}; padding: 8px; margin-bottom: 8px; display: flex; align-items: center; cursor: pointer; background-color: #f9f9f9; border-radius: 4px;">
                            <input type="checkbox" class="tag-check" data-tag-id="${tag.id}" value="${tag.id}" style="margin-right: 8px; cursor: pointer;">
                            <span>${tag.name}</span>
                        </label>
                    `)
                    .join('');

                // Re-add event listeners
                document.querySelectorAll('.tag-check').forEach(checkbox => {
                    checkbox.addEventListener('change', (e) => {
                        const modal = document.getElementById('tagModal');
                        const folderName = modal.dataset.folder;
                        const filename = modal.dataset.filename;
                        const tagId = e.target.dataset.tagId;

                        toggleImageTag(folderName, filename, tagId, e.target.checked);
                    });
                });
            }
        });
}

function loadImageTags(folderName, filename) {
    fetch(`/api/image-tags/${folderName}/${filename}`)
        .then(r => r.json())
        .then(data => {
            if (data.tags && data.tags.length > 0) {
                data.tags.forEach(tag => {
                    const checkbox = document.querySelector(`.tag-check[data-tag-id="${tag.id}"]`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
        })
        .catch(err => console.error('Error loading image tags:', err));
}

function toggleImageTag(folderName, filename, tagId, isAdding) {
    const method = isAdding ? 'POST' : 'DELETE';

    fetch(`/api/image-tag/${folderName}/${filename}/${tagId}`, {
        method: method
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showNotification(isAdding ? 'Tag added' : 'Tag removed', 'success');
            } else {
                showNotification(data.message || 'Error updating tag', 'error');
            }
        })
        .catch(err => {
            console.error('Error toggling tag:', err);
            showNotification('Error updating tag', 'error');
        });
}

function createNewTag() {
    const tagName = document.getElementById('newTagName').value.trim();
    const tagColor = document.getElementById('newTagColor').value;

    if (!tagName) {
        showNotification('Please enter a tag name', 'error');
        return;
    }

    fetch('/api/tags', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: tagName,
            color: tagColor
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('newTagName').value = '';
                document.getElementById('newTagColor').value = '#3498db';
                updateTagsList();
                showNotification('Tag created successfully', 'success');
            } else {
                showNotification(data.message || 'Error creating tag', 'error');
            }
        })
        .catch(err => {
            console.error('Error creating tag:', err);
            showNotification('Error creating tag', 'error');
        });
}

// Video duration calculation and display
function calculateVideoDurations() {
    const videos = document.querySelectorAll('.gallery-video');

    videos.forEach(video => {
        const durationElement = video.parentElement.querySelector('.video-duration');

        if (durationElement && video.readyState >= 1) {
            // Duration is available
            const duration = video.duration;
            if (!isNaN(duration) && isFinite(duration)) {
                const minutes = Math.floor(duration / 60);
                const seconds = Math.floor(duration % 60);
                durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        } else {
            // Duration not ready yet, wait for metadata
            video.addEventListener('loadedmetadata', () => {
                const duration = video.duration;
                if (!isNaN(duration) && isFinite(duration)) {
                    const minutes = Math.floor(duration / 60);
                    const seconds = Math.floor(duration % 60);
                    durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            });

            // Fallback: try to load metadata
            video.addEventListener('loadstart', () => {
                if (video.readyState >= 1) {
                    const duration = video.duration;
                    if (!isNaN(duration) && isFinite(duration)) {
                        const minutes = Math.floor(duration / 60);
                        const seconds = Math.floor(duration % 60);
                        durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    }
                }
            });
        }
    });
}

// Initialize video duration calculation when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for videos to load, then calculate durations
    setTimeout(calculateVideoDurations, 500);

    // Also calculate when new images are loaded (for lazy loading)
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE && node.querySelector('.gallery-video')) {
                        setTimeout(calculateVideoDurations, 100);
                    }
                });
            }
        });
    });

    const grid = document.querySelector('.image-grid');
    if (grid) {
        observer.observe(grid, { childList: true, subtree: true });
    }
});

/* Fullscreen touch swipe support (handle browser native fullscreen on mobile/iOS) */
let _fsTouch = {
    startX: 0,
    startY: 0,
    handlerStart: null,
    handlerEnd: null
};

function enableFullscreenTouchHandlers(targetEl) {
    // attach handlers to document to catch touches in fullscreen UI
    disableFullscreenTouchHandlers();

    _fsTouch.handlerStart = function(e) {
        if (e.touches && e.touches.length > 0) {
            _fsTouch.startX = e.touches[0].clientX;
            _fsTouch.startY = e.touches[0].clientY;
        }
    };

    _fsTouch.handlerEnd = function(e) {
        const endX = (e.changedTouches && e.changedTouches.length > 0) ? e.changedTouches[0].clientX : _fsTouch.startX;
        const endY = (e.changedTouches && e.changedTouches.length > 0) ? e.changedTouches[0].clientY : _fsTouch.startY;
        const deltaX = _fsTouch.startX - endX;
        const deltaY = _fsTouch.startY - endY;

        const absX = Math.abs(deltaX);
        const absY = Math.abs(deltaY);

        const vertThreshold = 40;
        const horizThreshold = 40;

        // If the fullscreen element is a video (or contains one), prefer vertical swipes
        const isVideoFS = (targetEl && (targetEl.tagName === 'VIDEO' || targetEl.querySelector && targetEl.querySelector('video')));

        if (isVideoFS && absY > Math.max(absX, vertThreshold)) {
            if (deltaY > vertThreshold) {
                // swipe up -> next
                nextImage();
            } else if (deltaY < -vertThreshold) {
                // swipe down -> prev
                prevImage();
            }
        } else if (!isVideoFS && absX > Math.max(absY, horizThreshold)) {
            if (deltaX > horizThreshold) nextImage();
            else if (deltaX < -horizThreshold) prevImage();
        }
    };

    document.addEventListener('touchstart', _fsTouch.handlerStart, { passive: true });
    document.addEventListener('touchend', _fsTouch.handlerEnd, { passive: true });
}

function disableFullscreenTouchHandlers() {
    if (_fsTouch.handlerStart) document.removeEventListener('touchstart', _fsTouch.handlerStart);
    if (_fsTouch.handlerEnd) document.removeEventListener('touchend', _fsTouch.handlerEnd);
    _fsTouch.handlerStart = null;
    _fsTouch.handlerEnd = null;
}

function _onFullScreenChange() {
    const fsEl = document.fullscreenElement || document.webkitFullscreenElement || null;
    if (fsEl) {
        // attach handlers to the fullscreen element (or document)
        enableFullscreenTouchHandlers(fsEl);
    } else {
        disableFullscreenTouchHandlers();
    }
}

// Listen for standard and webkit fullscreen change events
document.addEventListener('fullscreenchange', _onFullScreenChange);
document.addEventListener('webkitfullscreenchange', _onFullScreenChange);

// iOS Safari also fires webkitbeginfullscreen / webkitendfullscreen on the video element
function _attachWebkitHandlersToVideos() {
    document.querySelectorAll('video').forEach(v => {
        // when video enters native fullscreen on iOS
        v.addEventListener('webkitbeginfullscreen', (e) => {
            try {
                enableFullscreenTouchHandlers(v);
            } catch (err) {}
        });
        v.addEventListener('webkitendfullscreen', (e) => {
            try {
                disableFullscreenTouchHandlers();
            } catch (err) {}
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    _attachWebkitHandlersToVideos();
    // Re-attach when new videos are added (e.g., lazy load)
    const mo = new MutationObserver((mutations) => {
        mutations.forEach(m => {
            if (m.addedNodes) {
                m.addedNodes.forEach(n => {
                    if (n.nodeType === 1 && n.tagName === 'VIDEO') {
                        _attachWebkitHandlersToVideos();
                    } else if (n.nodeType === 1 && n.querySelector && n.querySelector('video')) {
                        _attachWebkitHandlersToVideos();
                    }
                });
            }
        });
    });
    const gridEl = document.getElementById('imagesGrid');
    if (gridEl) mo.observe(gridEl, { childList: true, subtree: true });
});
