import re
import os
import html
import argparse
from dotenv import load_dotenv


def parse_chat(file_path):
    message_pattern = re.compile(
        r"^\[(\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}:\d{2})\] ([^:]+): (.*)$"
    )
    messages = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = message_pattern.match(line)
            if match:
                date, sender, content = match.groups()
                messages.append({
                    "date": date,
                    "sender": sender,
                    "content": content
                })
            elif messages:
                messages[-1]["content"] += " " + line
    return messages



def format_content(raw_content, media_dir):
    """Format message content and return HTML + whether it has a file."""
    has_file = False
    content_html = html.escape(raw_content)

    if "pièce jointe" in raw_content:
        has_file = True
        filename = raw_content.split("pièce jointe :")[-1].strip(" ‎<>")
        filepath = os.path.join(media_dir, filename)

        ext = filename.lower().split('.')[-1]
        if ext in ["jpg", "jpeg", "png", "webp"]:
            content_html = f'<img src="{filepath}" class="media-img" alt="Image">'
        elif ext == "opus":
            content_html = f'<audio controls src="{filepath}"></audio>'
        else:
            content_html = f'<a href="{filepath}">📎 {filename}</a>'

    return content_html, has_file

def render_sub_message(raw_content, msg_time, media_dir):
    """Render a single sub-message into HTML."""
    content_html, has_file = format_content(raw_content, media_dir)
    sub_class = "with-file" if has_file else ""
    return f"""
        <div class="sub-message {sub_class}">
            <div class="text">{content_html}</div>
            <div class="time">{msg_time}</div>
        </div>
    """

def render_group_for_sender(messages, start_index, current_sender, your_name, media_dir):
    """Render all consecutive messages from the same sender."""
    i = start_index
    group_texts = []
    bubble_class = "sent" if your_name in current_sender else "received"

    while i < len(messages) and messages[i]["sender"] == current_sender:
        group_texts.append(render_sub_message(messages[i]["content"], messages[i]["date"], media_dir))
        i += 1

    html_block = f"""
        <div class="message {bubble_class}">
            <div class="sender">{current_sender}</div>
            {''.join(group_texts)}
        </div>
    """
    return html_block, i

def render_grouped_messages(messages, your_name, media_dir):
    """
    Render messages grouped by sender into HTML.
    Returns: [HTML, attendees, (start_date, end_date)]
    """
    if not messages:
        return ["", [], ("", "")]

    grouped_html = []
    i = 0
    attendees = list(set([msg["sender"] for msg in messages]))
    start_date = messages[0]["date"]
    end_date = messages[-1]["date"]

    while i < len(messages):
        current_sender = messages[i]["sender"]
        html_block, i = render_group_for_sender(messages, i, current_sender, your_name, media_dir)
        grouped_html.append(html_block)

    return ["\n".join(grouped_html), attendees, (start_date, end_date)]



def build_html(messages,your_name,media_dir):
    result = render_grouped_messages(messages,your_name,media_dir)
    grouped_html = result[0]
    attendees = result[1]
    start_date, end_date = result[2]

    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Conversation WhatsApp</title>
  <style>
    body {{
        font-family: Arial, sans-serif;
        background: #ece5dd;
        margin: 0;
        padding: 20px;
    }}
    .chat-container {{
        max-width: 800px;
        margin: auto;
        background: #fff;
        border-radius: 10px;
        padding: 20px;
    }}
    .message {{
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
        max-width: 70%;
    }}
    .sent {{
        background: #dcf8c6;
        margin-left: auto;
    }}
    .received {{
        background: #ECE5DD;
        border: 1px solid #ddd;
    }}
    .sub-message .text {{
        padding: 5px 10px;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 2px;
    }}
    .with-file .text {{
        background: #ECE5DD; 
        padding: 5px;
        border-radius: 8px;
        display: inline-block;
    }}
    .sender {{
        font-weight: bold;
        margin-bottom: 5px;
    }}
    .time {{
        font-size: 0.8em;
        color: #555;
        text-align: right;
    }}
    .media-img {{
        max-width: 200px;
        border-radius: 8px;
    }}
    .conversation-header {{
    text-align: center;
    margin-bottom: 15px;
    padding: 10px;
    background: #f1f1f1;
    border-radius: 10px;
    font-family: sans-serif;
    }}
    .conversation-header h2 {{
        margin: 0;
        font-size: 18px;
        font-weight: bold;
    }}
    .conversation-header p {{
        margin: 5px 0 0;
        font-size: 14px;
        color: #555;
    }}
  </style>
</head>
<body>
    <div class="conversation-header">
        <h2>Conversation between {' and '.join(attendees)}</h2>
    <p>Du {start_date} au {end_date}</p>
    </div>

  <div class="chat-container">
    {grouped_html}
  </div>
</body>
</html>
"""
def launch():
    load_dotenv()

    default_chat_file = os.getenv("CHAT_FILE", "chat.txt")
    default_media_dir = os.getenv("MEDIA_DIR", "media")
    default_output_file = os.getenv("OUTPUT_FILE", "output.html")
    default_your_name = os.getenv("YOUR_NAME", "Admin")

    parser = argparse.ArgumentParser(
        description="Generate HTML from WhatsApp exported chat with media."
    )
    parser.add_argument("--chat_file", type=str, default=default_chat_file,
                        help=f"Path to the exported chat file (default: {default_chat_file})")
    parser.add_argument("--media_dir", type=str, default=default_media_dir,
                        help=f"Directory containing media files (default: {default_media_dir})")
    parser.add_argument("--output_file", type=str, default=default_output_file,
                        help=f"Path to output HTML file (default: {default_output_file})")
    parser.add_argument("--your_name", type=str, default=default_your_name,
                        help=f"Your name to identify sent messages (default: {default_your_name})")

    args = parser.parse_args()
    chat_file = args.chat_file
    media_dir = args.media_dir
    output_file = args.output_file
    your_name = args.your_name

    print(f"Chat file   : {chat_file}")
    print(f"Media dir   : {media_dir}")
    print(f"Output file : {output_file}")
    print(f"Your name   : {your_name}")
    messages = parse_chat(chat_file)
    html_output = build_html(messages, your_name, media_dir)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"✅ File Generated : {output_file}")


if __name__ == "__main__":
    launch()
