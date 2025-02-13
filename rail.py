import os
from telethon import TelegramClient, events
import re
import pytesseract
import cv2
import numpy as np
import asyncio

# ✅ Replace with your actual Telegram API credentials
API_ID = 28738140  # Your API ID
API_HASH = "2396c79d7d76548be8d894ac0bf5d88a"  # Your API Hash
PHONE_NUMBER = "+919165762977"  # Your Telegram phone number

# ✅ MULTI-CHANNEL SUPPORT: Add multiple channel IDs
CHANNELS_TO_MONITOR = {
    -1001574277898: "COLORWIZ LOOT MODE ON",
    -1001503280854: "COOE LOOT MODE ON",
    -1002273735907: "SCRIPT TEST GROUP"
}

# ✅ TO ALERT (Where to send notifications)
ALERT_CHAT_ID = -1002270008878  # Your Group ID or User ID

# ✅ Create the Telegram Client
client = TelegramClient('alert_session', API_ID, API_HASH)

# ✅ Configure Tesseract OCR (Update path if necessary)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ✅ Dictionary to track which channels are sending alerts
chat_opened = {channel_id: False for channel_id in CHANNELS_TO_MONITOR.keys()}
message_count = 0  # ✅ Counter to track the number of processed messages

def clear_console():
    """Clears the CMD window every 50 messages to prevent overflow."""
    global message_count
    message_count += 1
    if message_count % 50 == 0:  # ✅ Clear CMD after every 50 messages
        os.system("cls" if os.name == "nt" else "clear")  # ✅ Works on Windows & Linux
        print("🧹 CMD Window Cleared to Prevent Overflow")

def extract_number_from_text(message):
    """Extracts the first number found in a message."""
    match = re.search(r'\b\d+\b', message)
    return match.group(0) if match else None

def extract_number_from_image(image_path):
    """Extracts numbers from an image using OCR (Tesseract)."""
    print(f"🔍 Processing image: {image_path}")

    # Read image using OpenCV
    image = cv2.imread(image_path)
    if image is None:
        print("❌ Error: Could not read image.")
        return []

    # Convert image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply adaptive threshold for better OCR detection
    gray = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )

    # Extract text using OCR
    extracted_text = pytesseract.image_to_string(gray)
    
    # ✅ Normalize spaces & commas to prevent number splitting
    extracted_text = extracted_text.replace(" ", "").replace(",", "")

    # ✅ Extract numbers from the processed text
    numbers = re.findall(r'\b\d+\b', extracted_text)
    print(f"🔢 Detected Numbers: {numbers}")

    return numbers

async def send_continuous_alert(channel_id, message_text, extracted_number):
    """Sends alert every 5 seconds until chat is opened for that specific channel."""
    global chat_opened
    channel_name = CHANNELS_TO_MONITOR.get(channel_id, "Unknown Channel")
    while not chat_opened[channel_id]:
        print(f"🚨 Detected '{extracted_number}' in {channel_name}, sending alert!")
        await client.send_message(
            ALERT_CHAT_ID,
            f'🚨 ALERT from **{channel_name}**!\n"{extracted_number}" detected:\n\n{message_text}'
        )
        await asyncio.sleep(5)  # ✅ Wait 5 seconds before sending again

async def process_message(event):
    """Handles both text and image messages, checking for '24300' or '72900'."""
    global chat_opened
    channel_id = event.chat_id  # Get the channel ID
    channel_name = CHANNELS_TO_MONITOR.get(channel_id, "Unknown Channel")

    message_text = event.message.message.strip() if event.message.message else ""

    # ✅ Check if text message contains "24300" or "72900"
    extracted_number = extract_number_from_text(message_text)
    if extracted_number in ["24300", "72900"]:
        chat_opened[channel_id] = False  # ✅ Reset flag to start continuous alerts
        await send_continuous_alert(channel_id, message_text, extracted_number)
        clear_console()  # ✅ Clear CMD window periodically
        return

    # ✅ If message contains an image, download and check for numbers
    if event.message.media:
        print(f"📸 Image detected in {channel_name}, processing OCR...")
        photo_path = await event.message.download_media()
        detected_numbers = extract_number_from_image(photo_path)

        for num in detected_numbers:
            if num in ["24300", "72900"]:
                chat_opened[channel_id] = False  # ✅ Reset flag to start continuous alerts
                await send_continuous_alert(channel_id, f'Number detected in image: {num}', num)
                clear_console()  # ✅ Clear CMD window periodically
                return

async def monitor_user_response():
    """Stops alerts when the user sends a message in the alert group."""
    global chat_opened
    async for message in client.iter_messages(ALERT_CHAT_ID, limit=1):
        if message.sender_id:
            for channel_id in chat_opened:
                chat_opened[channel_id] = True  # ✅ Stop alerts for all channels
            print("✅ Chat opened! Stopping alerts.")
            await client.send_message(ALERT_CHAT_ID, "✅ Chat opened! Alerts stopped.")

async def main():
    await client.start(PHONE_NUMBER)

    @client.on(events.NewMessage(chats=list(CHANNELS_TO_MONITOR.keys())))
    async def handler(event):
        """Handles incoming messages from multiple channels and checks for alerts."""
        await process_message(event)

    @client.on(events.NewMessage(chats=ALERT_CHAT_ID))
    async def stop_alert(event):
        """Stops alerts when user sends a message in the alert chat."""
        global chat_opened
        for channel_id in chat_opened:
            chat_opened[channel_id] = True
        print("✅ Chat opened! Stopping alerts.")
        await client.send_message(ALERT_CHAT_ID, "✅ Chat opened! Alerts stopped.")

    print("🤖 Bot is running... Monitoring multiple channels...")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
