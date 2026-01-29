#!/bin/bash

# Configuration
PLIST_NAME="com.solkos.discordbot.plist"
INSTALL_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$INSTALL_DIR/$PLIST_NAME"
PROJECT_DIR="$(pwd)"
PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/src/main.py"

# Ensure log directory exists
mkdir -p "$HOME/Library/Logs/com.solkos.discordbot"

# Create the .plist file
cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.solkos.discordbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/start_bot.sh</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/com.solkos.discordbot/bot.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/com.solkos.discordbot/bot.error.log</string>
</dict>
</plist>
EOF

echo "✅ Launch Agent created at: $PLIST_PATH"

# Unload if exists (to refresh)
launchctl unload "$PLIST_PATH" 2>/dev/null

# Load the new agent
launchctl load "$PLIST_PATH"

echo "🚀 Bot is now running in the background!"
echo "📄 Logs are being written to: $PROJECT_DIR/logs/"
echo "💡 The bot will automatically restart if it crashes or when you log in."
