# WhatsApp Chat Viewer

This project allows you to view exported WhatsApp chat logs in a clean HTML page, including messages, attachments (images, audio), and timestamps.

## Features
- Group consecutive messages by the same sender.
- Display images and audio attachments inline.
- Show individual timestamps for each message.
- Automatically generate a header with participants and conversation time range.

## Usage
1. Place your exported WhatsApp `.txt` files in the project folder.
2. Adjust `YOUR_NAME` in `chat_parser.py` to identify your messages.
3. Run the Python script to generate `index.html`:
```bash
python3 chat_parser.py
