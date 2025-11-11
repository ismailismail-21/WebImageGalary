// Global app configuration
const APP = {
    dataset_path: '/api'
};

// Navigate to folder from dropdown
function navigateToFolder(path) {
    if (path) {
        window.location.href = path;
    }
}

// Favorites dropdown functionality
document.addEventListener('DOMContentLoaded', () => {
    const favoritesBtn = document.querySelector('.favorites-btn');
    const favoritesMenu = document.querySelector('.favorites-menu');

    if (favoritesBtn && favoritesMenu) {
        favoritesBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            favoritesMenu.classList.toggle('active');
        });

        document.addEventListener('click', () => {
            favoritesMenu.classList.remove('active');
        });

        favoritesMenu.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
});

// Load favorites
function loadFavorites() {
    const favoritesMenu = document.getElementById('favoritesMenu');
    if (!favoritesMenu) return;

    fetch('/api/favorites')
        .then(r => r.json())
        .then(favorites => {
            if (favorites.length === 0) {
                favoritesMenu.innerHTML = '<div class="favorites-empty">No favorites yet</div>';
            } else {
                favoritesMenu.innerHTML = favorites
                    .map(fav => `<a href="/folder/${fav.folder_path}" class="favorite-item">${fav.folder_path}</a>`)
                    .join('');
            }
        })
        .catch(err => console.error('Error loading favorites:', err));
}

// Initial load
if (document.readyState !== 'loading') {
    loadFavorites();
} else {
    document.addEventListener('DOMContentLoaded', loadFavorites);
}
