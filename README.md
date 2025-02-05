# Zabbix Telegram Notifier

This Python script integrates with Zabbix API to fetch and notify about active problems via Telegram. It periodically checks for high severity issues and sends alerts to a specified Telegram chat.

## Requirements

- Python 3.7 or higher
- Zabbix 7.2.2
- `requests` library
- `asyncio` library 
- `telegram` library (install via `pip install python-telegram-bot`)

## Setup

1. **Zabbix API Credentials**:
   - Update `zabbix_url`, `zabbix_user`, and `zabbix_pass` variables with your Zabbix API endpoint and credentials.

2. **Telegram Bot Credentials**:
   - Obtain a bot token from BotFather on Telegram and update the `telegram_bot_token` field from the json file.
   - Replace `telegram_chat_id` with your chat ID where you want to receive notifications.

3. **Debug Mode**:
   - Add `--debug True` to the command to run the script for testing purposes to use the debug bot token and chat ID.

4. **Execution**:
   - Run the script. It will authenticate with Zabbix API, fetch active problems, format alerts, and send them to the specified Telegram chat.

