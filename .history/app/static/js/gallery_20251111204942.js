// Gallery functionality with tags and justified layout
let currentImageIndex = 0;
let allImages = [];
let currentFolderName = '';

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
    const favoriteBtn = document.querySelector('.lightbox-favorite');

    if (favoriteImages.has(filename)) {
        favoriteBtn.classList.add('active');
    } else {
        favoriteBtn.classList.remove('active');
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
