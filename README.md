# 🍊 Orange Carrier Active Range Bot

## 📁 File Structure
```
orange_bot/
├── bot.py              # Main entry point
├── config.py           # Bot token, admin ID, credentials
├── database.py         # SQLite database
├── scraper.py          # Orange Carrier web scraper
├── scheduler.py        # Auto check scheduler
├── formatter.py        # Message formatter
├── requirements.txt    # Dependencies
└── handlers/
    ├── start.py        # /start command
    ├── admin.py        # Admin panel UI
    ├── callbacks.py    # All button handlers
    ├── subscription.py # Subscription flow
    └── messages.py     # Text & file input handler
```

## ⚙️ Setup

### 1. Install Python 3.10+

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the bot
```bash
python bot.py
```

## 🚀 VPS Deployment (Recommended)

### Run as background service
```bash
# Install screen
sudo apt install screen

# Start in screen session
screen -S orangebot
python bot.py

# Detach: Ctrl+A then D
# Reattach: screen -r orangebot
```

### Or use systemd service
```bash
sudo nano /etc/systemd/system/orangebot.service
```
```ini
[Unit]
Description=Orange Carrier Bot
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/orange_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable orangebot
sudo systemctl start orangebot
```

## 📋 Admin Commands
- `/start` - Start the bot
- `/admin` - Open admin panel

## ✨ Features
- 📡 Auto CLI search on Orange Carrier
- 👥 User management (ban/unban)
- 💳 Subscription system (manual approval)
- 📦 Multiple plans with custom pricing
- 💰 Multiple payment methods
- 📢 Broadcast to all/subscribers
- ⚙️ All settings from admin panel
- 📋 CLI bulk import (txt/csv)
- 🔄 Auto scheduler with custom interval
