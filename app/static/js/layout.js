// Smart Image Layout Algorithm
// Arranges images in rows to minimize gaps (like Google Photos/Flickr)

class SmartGalleryLayout {
    constructor(containerSelector, containerHeight = 200, gap = 8) {
        this.container = document.querySelector(containerSelector);
        this.containerHeight = containerHeight;
        this.gap = gap;
        this.items = [];
    }

    /**
     * Calculate layout for images
     * Returns array of rows, each row contains items with calculated widths
     */
    calculateLayout() {
        if (!this.container) return;

        const items = Array.from(this.container.querySelectorAll('.grid-item'));
        if (items.length === 0) return;

        const containerWidth = this.container.clientWidth;
        const rows = this.arrangeIntoRows(items, containerWidth);
        this.applyLayout(rows, containerWidth);
    }

    /**
     * Arrange items into rows
     */
    arrangeIntoRows(items, containerWidth) {
        const rows = [];
        let currentRow = [];
        let currentRowAspectRatio = 0;

        for (let item of items) {
            const aspectRatio = parseFloat(item.dataset.aspectRatio) || 1;
            currentRow.push({ item, aspectRatio });
            currentRowAspectRatio += aspectRatio;

            // Calculate if row should be complete
            const availableWidth = containerWidth - (currentRow.length - 1) * this.gap;
            const rowHeight = availableWidth / currentRowAspectRatio;

            // If row height is reasonable (between 100px and 300px), keep it
            // Otherwise, complete the row
            if (rowHeight < 150 || currentRow.length >= 6) {
                rows.push([...currentRow]);
                currentRow = [];
                currentRowAspectRatio = 0;
            }
        }

        // Add remaining items
        if (currentRow.length > 0) {
            rows.push(currentRow);
        }

        return rows;
    }

    /**
     * Apply calculated layout to DOM
     */
    applyLayout(rows, containerWidth) {
        // Clear existing rows
        const grid = this.container;
        const existingRows = grid.querySelectorAll('.grid-row');
        existingRows.forEach(row => row.remove());

        // Create new rows
        for (let rowItems of rows) {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'grid-row';

            // Calculate total aspect ratio for this row
            let totalAspectRatio = 0;
            for (let { aspectRatio } of rowItems) {
                totalAspectRatio += aspectRatio;
            }

            // Calculate row height to fill width
            const availableWidth = containerWidth - (rowItems.length - 1) * this.gap;
            const rowHeight = availableWidth / totalAspectRatio;

            // Ensure reasonable height (clamped between min and max)
            const clampedHeight = Math.max(100, Math.min(300, rowHeight));

            // Position items in row
            for (let i = 0; i < rowItems.length; i++) {
                const { item, aspectRatio } = rowItems[i];
                const itemWidth = (clampedHeight * aspectRatio);

                item.style.height = clampedHeight + 'px';
                item.style.width = itemWidth + 'px';
                item.style.flex = 'none';
                item.style.margin = '0';

                rowDiv.appendChild(item);
            }

            rowDiv.style.gap = this.gap + 'px';
            grid.appendChild(rowDiv);
        }
    }

    /**
     * Recalculate on window resize
     */
    onWindowResize() {
        this.calculateLayout();
    }
}

// Initialize layout
let galleryLayout;

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('imagesGrid');
    if (grid) {
        galleryLayout = new SmartGalleryLayout('#imagesGrid', 200, 8);
        galleryLayout.calculateLayout();

        // Recalculate on resize
        window.addEventListener('resize', debounce(() => {
            galleryLayout.calculateLayout();
        }, 250));
    }
});

/**
 * Debounce helper
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
