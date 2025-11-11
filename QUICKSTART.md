# 🖼️ Web Image Gallery - Quick Start Guide

## ✅ Installation & Setup

The application is ready to use! Here's how to get started:

### Prerequisites
- Python 3.8+
- Your images in the `dataset/` folder (already configured)

### 1️⃣ First-Time Setup

```bash
cd /Users/x/Python/WebImageGalary

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Run the Gallery

```bash
source venv/bin/activate
python run.py
```

Then open your browser to: **http://localhost:5000**

### 💡 Quick Commands

```bash
# Using the dev helper script
chmod +x dev.sh

./dev.sh setup   # Setup everything
./dev.sh run     # Start server
./dev.sh clean   # Clean cache & database
```

---

## 🎯 Features Overview

### 📁 Folder Browsing
- All subfolders in `dataset/` are automatically detected
- Shows image count per folder
- Click any folder to view images

### 🎨 Smart Grid Layout
- Images automatically arrange based on aspect ratio
- No wasted space - masonry-style layout
- Different image sizes display beautifully together
- Responsive on desktop, tablet, and mobile

### 🖼️ Image Viewer
- **Full-screen lightbox** - Click any image to expand
- **Scroll wheel** - Navigate between images (next/previous)
- **Ctrl + Scroll** - Zoom in/out
- **Arrow keys** - Previous/Next image
- **Escape key** - Close lightbox

### ❤️ Favorites System
- Click the heart button (❤️) to add folder to favorites
- Heart turns red when added
- View all favorites from navbar dropdown
- Persists across sessions

### 🗑️ Delete Images
- Hover over any image
- Click the delete button (🗑️)
- Images deleted instantly (no confirmation needed)
- One-click, no questions asked

### 📄 Pagination
- 100 images per page
- Navigate with page buttons at the bottom
- Current page highlighted

---

## 📂 Project Structure

```
WebImageGalary/
├── app/                          # Main Flask application
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # Database models
│   ├── routes.py                # API endpoints
│   ├── utils.py                 # Utility functions
│   ├── templates/
│   │   ├── base.html            # Base template
│   │   ├── index.html           # Home page
│   │   └── folder.html          # Gallery page
│   └── static/
│       ├── css/
│       │   ├── style.css        # Global styles
│       │   └── gallery.css      # Gallery styles
│       └── js/
│           ├── app.js           # Global functionality
│           └── gallery.js       # Gallery features
│
├── dataset/                     # Your image folders (auto-detected)
│   ├── corba/
│   ├── salata/
│   ├── tatli/
│   ├── yemek/
│   └── ...
│
├── run.py                       # Entry point
├── requirements.txt             # Python dependencies
├── setup.sh                     # Setup script
├── dev.sh                       # Development helper
├── README.md                    # Full documentation
└── .env.example                 # Environment template
```

---

## 🔧 Configuration

Edit `.env` to customize:

```env
# Server
HOST=127.0.0.1
PORT=5000

# Environment
FLASK_ENV=development
FLASK_DEBUG=1

# Dataset
DATASET_PATH=./dataset
```

---

## 🚀 Features Implemented

✅ **Smart Grid Layout**
- Aspect ratio-aware image placement
- Masonry-style responsive grid
- Auto-scales based on image dimensions
- 200px base height, expands intelligently

✅ **Full-Screen Viewer**
- Click image to open lightbox
- Previous/Next navigation buttons
- Image counter (e.g., "1 / 50")
- Close button (top-right)

✅ **Scroll Navigation**
- Scroll wheel = Next/Previous image
- Ctrl+Scroll = Zoom in/out
- Works smoothly in fullscreen mode

✅ **Favorites System**
- Heart button per folder
- Visual indicator (red when favorited)
- Dropdown menu in navbar
- Persistent SQLite database

✅ **Delete Without Confirmation**
- One-click delete button on hover
- Instant removal from display
- Database cleanup automatic
- No confirmation dialog

✅ **Pagination**
- 100 images per page (configurable)
- Page number buttons
- First/Last shortcuts
- Shows current page

✅ **Multiple Formats**
- JPG, PNG, GIF, BMP, WebP, HEIC
- Auto-conversion support ready
- Works with existing dataset

✅ **Mobile Responsive**
- Works on phones & tablets
- Touch-friendly buttons
- Responsive grid layout
- Full-screen lightbox

---

## 📱 Usage Examples

### Viewing Your Gallery

1. **Start the server:**
   ```bash
   python run.py
   ```

2. **Open browser:** `http://localhost:5000`

3. **Browse folders:** Click any folder to see images

4. **View full-screen:** Click any image

5. **Navigate:** Use scroll wheel or arrow keys

6. **Add favorites:** Click heart button

7. **Delete image:** Hover and click delete button

---

## 🛠️ Customization

### Change Images Per Page

Edit `app/routes.py`, find `per_page = 100` and change to desired number.

### Adjust Grid Height

Edit `app/static/css/gallery.css`, change `grid-auto-rows: 200px` value.

### Modify Colors

Edit CSS files in `app/static/css/`:
- Primary color: `#667eea`
- Secondary: `#764ba2`
- Delete color: `#ff6b6b`

### Add New Features

All code is modular and well-commented. Add features by:
1. Backend: Extend `app/routes.py`
2. Frontend: Modify templates and static files
3. Database: Update `app/models.py`

---

## 📝 Important Notes

### Database
- SQLite database stored in root: `gallery.db`
- Auto-created on first run
- Delete to reset favorites

### Image Paths
- All image folders must be in `dataset/` directory
- Supports nested folders
- Auto-detects supported image formats

### Performance
- Large image collections may take time to load initially
- Consider optimizing images if >10MB each
- Caching improves subsequent loads

### Security
- Path traversal protection built-in
- Safe deletion with validation
- SQLite injection prevention

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 5000 is in use
lsof -i :5000

# Use different port
PORT=5001 python run.py
```

### Database errors
```bash
# Reset database
rm gallery.db
python run.py  # Recreates it
```

### Images not showing
```bash
# Check DATASET_PATH
echo $DATASET_PATH

# Set it explicitly
export DATASET_PATH=/Users/x/Python/WebImageGalary/dataset
python run.py
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📚 API Endpoints Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Home page |
| GET | `/folder/<name>` | View folder |
| GET | `/api/folders` | List all folders |
| GET | `/api/folder/<name>/images` | Get images with pagination |
| GET | `/api/image/<folder>/<file>` | Serve image file |
| POST | `/api/favorite/<folder>` | Add to favorites |
| DELETE | `/api/favorite/<folder>` | Remove from favorites |
| GET | `/api/favorites` | List favorites |
| DELETE | `/api/image/<folder>/<file>` | Delete image |

---

## 🎉 You're All Set!

The gallery is running and ready to use. Start exploring your images!

### Next Steps:
1. Open http://localhost:5000
2. Click on a folder to view images
3. Try the full-screen viewer
4. Add folders to favorites
5. Delete unwanted images

**Enjoy your web gallery! 🚀**
