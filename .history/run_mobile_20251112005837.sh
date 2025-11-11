#!/bin/bash
# Run the gallery server accessible from mobile devices on the same network

echo "🖼️  Starting Web Image Gallery for Mobile Access..."
echo ""
echo "📱 To access from your phone:"
echo "   1. Make sure your phone is on the same WiFi network"
echo "   2. On your Mac, get your IP address:"
echo "      System Settings → Network → WiFi → Details → TCP/IP"
echo "   3. On your phone, open browser and go to:"
echo "      http://YOUR_IP_ADDRESS:5000"
echo ""
echo "   Example: http://192.168.1.100:5000"
echo ""
echo "🌐 Server will be accessible on all network interfaces..."
echo ""

# Set HOST to 0.0.0.0 to allow connections from any device on the network
export HOST=0.0.0.0
export PORT=5000

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the server
python3 run.py
