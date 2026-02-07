/**
 * common.js - Common utilities and functions used across all pages
 */

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Encode URL path component properly
 */
function encodePathComponent(str) {
    return encodeURIComponent(str).replace(/%2F/g, '/');
}

/**
 * Build API URL with properly encoded path components
 */
function buildApiUrl(base, ...parts) {
    const encodedParts = parts.map(part => encodeURIComponent(part));
    return base + '/' + encodedParts.join('/');
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    // Remove any existing notification
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    const colors = {
        success: '#4CAF50',
        error: '#f44336',
        info: '#2196F3',
        warning: '#ff9800'
    };

    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${colors[type] || colors.info};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============================================================================
// IMAGE/FAVORITE FUNCTIONS
// ============================================================================

/**
 * Toggle favorite status for an image
 */
function toggleImageFavorite(folder, filename, buttonElement) {
    const isActive = buttonElement.classList.contains('active');
    const method = isActive ? 'DELETE' : 'POST';

    fetch(buildApiUrl('/api/favorite', folder, filename), { method })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                buttonElement.classList.toggle('active');
                buttonElement.textContent = buttonElement.classList.contains('active') ? '♥' : '♡';

                // If on home page, remove the card when unfavorited
                if (!buttonElement.classList.contains('active')) {
                    const favCard = buttonElement.closest('.favorite-card');
                    if (favCard) {
                        favCard.style.animation = 'fadeOut 0.3s ease';
                        setTimeout(() => favCard.remove(), 300);
                    }
                }
            }
        })
        .catch(err => {
            console.error('Error toggling favorite:', err);
            showNotification('Error updating favorite', 'error');
        });
}

/**
 * Delete an image
 */
function deleteImage(folder, filename, buttonElement) {
    if (!confirm(`Delete ${filename}?`)) return;

    fetch(buildApiUrl('/api/image', folder, filename), { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const gridItem = buttonElement.closest('.grid-item, .favorite-card');
                if (gridItem) {
                    gridItem.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => gridItem.remove(), 300);
                }
                showNotification('Image deleted', 'success');
            } else {
                showNotification(data.message || 'Failed to delete', 'error');
            }
        })
        .catch(err => {
            console.error('Error deleting image:', err);
            showNotification('Error deleting image', 'error');
        });
}

// ============================================================================
// TAG FUNCTIONS
// ============================================================================

/**
 * Load tags for an image
 */
function loadImageTags(folder, filename) {
    fetch(buildApiUrl('/api/image-tags', folder, filename))
        .then(r => r.json())
        .then(imageTags => {
            const tagsContainer = document.getElementById(`tags-${filename}`);
            if (tagsContainer && imageTags && imageTags.length > 0) {
                const tagHtml = imageTags
                    .map(it => `<span class="tag-badge" style="background-color: ${it.tag.color}">${it.tag.name}</span>`)
                    .join('');
                tagsContainer.innerHTML = tagHtml;
            } else if (tagsContainer) {
                tagsContainer.innerHTML = '';
            }
        })
        .catch(err => console.error('Error loading tags:', err));
}

/**
 * Check if image is favorited
 */
function checkImageFavorite(folder, filename) {
    fetch(buildApiUrl('/api/favorite', folder, filename))
        .then(r => r.json())
        .then(data => {
            const gridItem = document.querySelector(`[data-folder="${folder}"][data-filename="${filename}"]`);
            const heartBtn = gridItem?.querySelector('.heart-btn');
            if (heartBtn && data.is_favorite) {
                heartBtn.classList.add('active');
                heartBtn.textContent = '♥';
            }
        })
        .catch(err => console.error('Error checking favorite:', err));
}

/**
 * Toggle tag dropdown for an image
 */
function toggleTagDropdown(folder, filename) {
    const dropdown = document.getElementById(`tag-dropdown-${filename}`);

    // Close all other dropdowns
    document.querySelectorAll('.tag-dropdown').forEach(d => {
        if (d.id !== `tag-dropdown-${filename}`) {
            d.style.display = 'none';
        }
    });

    if (dropdown.style.display === 'none' || dropdown.style.display === '') {
        loadTagsForDropdown(folder, filename);
        dropdown.style.display = 'block';
    } else {
        dropdown.style.display = 'none';
    }
}

/**
 * Load tags into dropdown
 */
function loadTagsForDropdown(folder, filename) {
    const tagList = document.getElementById(`tag-list-${filename}`);
    if (!tagList) return;

    fetch('/api/tags')
        .then(r => r.json())
        .then(allTags => {
            if (allTags.length === 0) {
                tagList.innerHTML = '<div style="padding: 12px; color: #999; text-align: center; font-size: 0.85em;">No tags available<br><a href="/tags" style="color: #667eea;">Create tags</a></div>';
                return;
            }

            fetch(buildApiUrl('/api/image-tags', folder, filename))
                .then(r => r.json())
                .then(imageTags => {
                    const currentTagIds = imageTags.map(it => it.tag_id);

                    const tagHtml = allTags.map(tag => {
                        const isActive = currentTagIds.includes(tag.id);
                        return `
                            <div class="tag-dropdown-item ${isActive ? 'active' : ''}" 
                                 style="border-left-color: ${tag.color}"
                                 onclick="toggleTagForImage('${folder}', '${filename}', ${tag.id}, this)">
                                <input type="checkbox" 
                                       class="tag-dropdown-checkbox" 
                                       ${isActive ? 'checked' : ''}
                                       onclick="event.stopPropagation();">
                                <span>${tag.name}</span>
                            </div>
                        `;
                    }).join('');

                    tagList.innerHTML = tagHtml;
                });
        })
        .catch(err => {
            console.error('Error loading tags:', err);
            tagList.innerHTML = '<div style="padding: 12px; color: #e74c3c;">Error loading tags</div>';
        });
}

/**
 * Toggle tag assignment for image
 */
function toggleTagForImage(folder, filename, tagId, element) {
    const checkbox = element.querySelector('.tag-dropdown-checkbox');
    const isCurrentlyActive = checkbox.checked;

    checkbox.checked = !isCurrentlyActive;

    const method = isCurrentlyActive ? 'DELETE' : 'POST';
    fetch(buildApiUrl('/api/image-tag', folder, filename, tagId), { method })
        .then(r => {
            if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
            return r.json();
        })
        .then(data => {
            if (data.success) {
                element.classList.toggle('active', !isCurrentlyActive);
                setTimeout(() => loadImageTags(folder, filename), 100);
            } else {
                checkbox.checked = isCurrentlyActive;
                showNotification('Error: ' + (data.message || 'Failed to update tag'), 'error');
            }
        })
        .catch(err => {
            console.error('Error toggling tag:', err);
            checkbox.checked = isCurrentlyActive;
            showNotification('Error updating tag', 'error');
        });
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.tag-circle-btn') && !e.target.closest('.tag-dropdown')) {
        document.querySelectorAll('.tag-dropdown').forEach(d => {
            d.style.display = 'none';
        });
    }
});

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    @keyframes fadeOut {
        from { opacity: 1; transform: scale(1); }
        to { opacity: 0; transform: scale(0.9); }
    }
`;
document.head.appendChild(style);
