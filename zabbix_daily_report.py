import requests
import json
import time
import asyncio
import random
import os
from telegram import Bot
import argparse

# Load configuration from file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_FILE, "r", encoding="utf-8") as file:
    config = json.load(file)

# Extract settings from config
ZABBIX_URL = config["zabbix_url"]
ZABBIX_USER = config["zabbix_user"]
ZABBIX_PASS = config["zabbix_pass"]
MAX_MESSAGE_LENGTH = config["max_message_length"]
GOOD_MORNING_FILE = os.path.join(BASE_DIR, config["good_morning_file"])

# Command line argument for DEBUG mode
parser = argparse.ArgumentParser(description="Run the Zabbix Telegram Notifier.")
parser.add_argument("--debug", choices=["True", "False"], default="False", help="Set the debug mode (True or False)")
args = parser.parse_args()
DEBUG = args.debug == "True"

# Select Telegram credentials based on DEBUG mode
TELEGRAM_BOT_TOKEN = config["telegram_bot_token_debug"] if DEBUG else config["telegram_bot_token"]
TELEGRAM_CHAT_ID = config["telegram_chat_id_debug"] if DEBUG else config["telegram_chat_id"]

# Initialize Telegram Bot
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
    response_json = response.json()
    if "result" not in response_json:
        raise Exception(f"Authentication failed: {response_json.get('error', 'Unknown error')}")
    return response_json["result"]


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
    """Read a random line from the good morning file or return a default message."""
    try:
        with open(nombre_archivo, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()
            return random.choice(lineas).strip() if lineas else "Buenos días Pablo!"
    except FileNotFoundError:
        return "Buenos días Pablo!"


async def send_message(message):
    """Send message in chunks to avoid exceeding Telegram limits, with retries."""
    chunks = [message[i : i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

    for chunk in chunks:
        for attempt in range(3):  # Retry up to 3 times
            try:
                msg = await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode="Markdown")
                
                if msg:  # Telegram successfully processed the message
                    print(f"Successfully sent message: {msg.message_id}")
                    await asyncio.sleep(0.5)
                    break  # Exit retry loop if successful
            except Exception as e:
                print(f"Attempt {attempt + 1}: Failed to send message - {e}")
                await asyncio.sleep(5)  # Wait before retrying

        else:  # If all attempts fail
            print(f"Completely failed to send message after 3 attempts.")
            return False  # Indicate failure

    return True  # Indicate success



def format_alert(problems, event_host_map):
    """Format problems into a readable Telegram message."""
    message = "\U0001F4CA *Zabbix Daily Report*\n\n" + leer_linea_aleatoria(GOOD_MORNING_FILE) + "\n\n"
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
    """Main function to authenticate, fetch alerts, format, and send them."""
    for attempt in range(6):  # Retry fetching data up to 6 times
        try:
            auth_token = authenticate()
            problems = fetch_problems(auth_token)
            event_host_map = fetch_event_hosts(auth_token, [p["eventid"] for p in problems])
            message = format_alert(problems, event_host_map)

            if await send_message(message):  # Now send_message handles its own retries
                print("Report successfully sent.")
                return  # Exit on success
            else:
                print("Failed to send message, but will retry fetching data.")
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error fetching data - {e}")

        await asyncio.sleep(600)  # Wait 10 minutes before retrying


if __name__ == "__main__":
    asyncio.run(main())
