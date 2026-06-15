#!/bin/bash

# AWS EC2 Discord Bot Deployment Script
# Run this on your EC2 instance after connecting via SSH

echo "🚀 Starting Discord Bot deployment on AWS EC2..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "🐍 Installing Python, Git, and Nginx..."
sudo apt install python3 python3-pip python3-venv git nginx htop curl -y

# Clone repository (replace with your repo URL)
echo "📂 Cloning repository..."
cd /home/ubuntu
git clone https://github.com/FoodStyles-Tech-Tools/discordbotapi.git
cd your-discord-bot

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file template
echo "⚙️ Creating environment file template..."
cat > .env << EOF
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_token_here
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your_api_key_here

# AWS Configuration
AWS_REGION=us-east-1
ENVIRONMENT=production
EOF

echo "🔑 IMPORTANT: Edit .env file with your actual tokens:"
echo "nano .env"
echo ""

# Create systemd service
echo "📝 Creating systemd service..."
sudo tee /etc/systemd/system/discord-bot.service > /dev/null << EOF
[Unit]
Description=Discord Bot API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/your-discord-bot
Environment=PATH=/home/ubuntu/your-discord-bot/venv/bin
ExecStart=/home/ubuntu/your-discord-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration for reverse proxy
echo "🌐 Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/discord-bot > /dev/null << EOF
server {
    listen 80;
    server_name _;
    
    # Health check endpoint for ALB
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Web interface
    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/discord-bot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Set up log rotation
echo "📋 Setting up log rotation..."
sudo tee /etc/logrotate.d/discord-bot > /dev/null << EOF
/home/ubuntu/your-discord-bot/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload discord-bot
    endscript
}
EOF

echo ""
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. Edit your .env file:"
echo "   nano .env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable discord-bot"
echo "   sudo systemctl start discord-bot"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status discord-bot"
echo "   sudo journalctl -u discord-bot -f"
echo ""
echo "4. Test endpoints:"
echo "   curl http://localhost/health"
echo "   curl http://\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/health"
echo ""
echo "🌐 Your bot will be accessible at:"
echo "   http://\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo ""
echo "📊 Monitor with:"
echo "   htop"
echo "   sudo journalctl -u discord-bot -f"
echo "   sudo journalctl -u nginx -f"