import requests
import json
import time
import asyncio
import random
from telegram import Bot
import argparse

# Zabbix API Credentials
ZABBIX_URL = "http://xxx.xxx.xxx.xxx/zabbix/api_jsonrpc.php"
ZABBIX_USER = "Admin"
ZABBIX_PASS = "zabbix"

# Command line argument for DEBUG mode
parser = argparse.ArgumentParser(description="Run the Zabbix Telegram Notifier.")
parser.add_argument(
    "--debug", 
    choices=["True", "False"], 
    default="False", 
    help="Set the debug mode (True or False)"
)
args = parser.parse_args()

DEBUG = args.debug == "True"

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = (
    "xxxxxx"
    if DEBUG
    else "xxxxxx"
)
TELEGRAM_CHAT_ID = "xxxxxx" if DEBUG else "xxxxxx"

MAX_MESSAGE_LENGTH = 4096
bot = Bot(token=TELEGRAM_BOT_TOKEN)


def authenticate():
    """Authenticate with Zabbix API and return the auth token."""
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {"username": ZABBIX_USER, "password": ZABBIX_PASS},
        "id": 1,
    }
    response = requests.post(ZABBIX_URL, json=payload, headers={"Content-Type": "application/json-rpc"})
    auth_token = response.json().get("result")
    if not auth_token:
        raise Exception("Authentication failed, check credentials.")
    return auth_token


def fetch_problems(auth_token):
    """Fetch active problems from Zabbix API."""
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json-rpc"}
    payload = {
        "jsonrpc": "2.0",
        "method": "problem.get",
        "params": {"output": ["eventid", "clock", "name", "severity"]},
        "id": 2,
    }
    response = requests.post(ZABBIX_URL, json=payload, headers=headers)
    problems = response.json().get("result", [])
    return [p for p in problems if int(p["severity"]) == 5] if not DEBUG else problems


def fetch_event_hosts(auth_token, event_ids):
    """Fetch host details for given event IDs."""
    if not event_ids:
        return {}
    
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json-rpc"}
    payload = {
        "jsonrpc": "2.0",
        "method": "event.get",
        "params": {"output": ["eventid", "name"], "eventids": event_ids, "selectHosts": ["host", "name"]},
        "id": 3,
    }
    response = requests.post(ZABBIX_URL, json=payload, headers=headers)
    events = response.json().get("result", [])
    return {event["eventid"]: event.get("hosts", []) for event in events}


def leer_linea_aleatoria(nombre_archivo):
    """Read a random line from the given file or return a default message."""
    try:
        with open(nombre_archivo, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()
            return random.choice(lineas).strip() if lineas else "Buenos días Pablo!"
    except FileNotFoundError:
        return "Buenos días Pablo!"


async def send_message(message):
    """Send message in chunks to avoid exceeding Telegram limits."""
    chunks = [message[i : i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
    for chunk in chunks:
        try:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode="Markdown")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Failed to send message: {e}")


def format_alert(problems, event_host_map):
    """Format problems into a readable Telegram message."""
    message = "\U0001F4CA *Zabbix Daily Report*\n\n" + leer_linea_aleatoria("good_morning_pablo.txt") + "\n\n"
    if not problems:
        return message + "✅ No issues found!"

    event_messages = []
    for problem in problems:
        event_id = problem["eventid"]
        trigger = problem["name"]
        severity = problem["severity"]
        event_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(problem["clock"])))
        host_names = ", ".join([host["name"] for host in event_host_map.get(event_id, [])]) or "Unknown Host"
        
        event_messages.append(
            f"⚠️ *Problem:* {trigger}\n"
            f"👤 *Host:* http://{host_names}\n"
            f"⏰ *Time:* {event_time}\n"
            f"🔹 *EventID:* {event_id}\n"
            + (f"🔥 *Severity:* {severity}\n" if DEBUG else "")
        )
    return message + "\n".join(event_messages)


async def main():
    for _ in range(6):
        try:
            auth_token = authenticate()
            problems = fetch_problems(auth_token)
            event_host_map = fetch_event_hosts(auth_token, [p["eventid"] for p in problems])
            message = format_alert(problems, event_host_map)
            await send_message(message)
            print("Report Successfully sent report.")
            return
        except Exception as e:
            print(f"Error: {e}")
        
        await asyncio.sleep(600)


if __name__ == "__main__":
    asyncio.run(main())
