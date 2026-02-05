sudo apt install ffmpeg imagemagick parallel
sudo dnf install ffmpeg ImageMagick parallel
ffmpeg -version
convert --version
parallel --version
chmod +x generate_thumbnails.sh
./generate_thumbnails.sh --size 400 --jobs 8