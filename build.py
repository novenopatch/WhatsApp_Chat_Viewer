import re
import os
import html


message_pattern = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}:\d{2})\] ([^:]+): (.*)$"
)

def parse_chat(file_path):
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

def render_grouped_messages(messages,your_name,media_dir):
    """
       Render messages grouped by sender into HTML.
       messages: liste of dict { 'sender', 'content', 'date' }
       your_name: one username to distinguish sent and received messages
       media_dir: media directory
       Returns: [HTML, attendees, (start_date, end_date)]
    """
    grouped_html = []
    i = 0
    attendees = list(set([msg["sender"] for msg in messages]))
    start_date = messages[0]["date"]
    end_date = messages[-1]["date"]
    while i < len(messages):
        current_sender = messages[i]["sender"]
        bubble_class = "sent" if your_name in current_sender else "received"

        group_texts = []

        while i < len(messages) and messages[i]["sender"] == current_sender:
            raw_content = messages[i]["content"]
            msg_time = messages[i]["date"]

            has_file = False
            if "pièce jointe" in raw_content:
                has_file = True
                filename = raw_content.split("pièce jointe :")[-1].strip(" ‎<>")
                filepath = os.path.join(media_dir, filename)

                if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    content = f'<img src="{filepath}" class="media-img" alt="Image">'
                elif filename.lower().endswith(".opus"):
                    content = f'<audio controls src="{filepath}"></audio>'
                else:
                    content = f'<a href="{filepath}">📎 {filename}</a>'
            else:
                content = html.escape(raw_content)

            sub_message_class = "with-file" if has_file else ""
            group_texts.append(f"""
                <div class="sub-message {sub_message_class}">
                    <div class= text>{content}</div>
                    <div class="time">{msg_time}</div>
                </div>
            """)

            i += 1

        grouped_html.append(f"""
        <div class="message {bubble_class}">
            <div class="sender">{current_sender}</div>
            {''.join(group_texts)}
        </div>
        """)

    return ["\n".join(grouped_html),attendees,(start_date,end_date)]





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

if __name__ == "__main__":
    chat_file = "chat.txt"
    media_dir = "media"
    output_file = "output.html"
    your_name = ""
    messages = parse_chat(chat_file)
    html_output = build_html(messages,your_name,media_dir)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"✅ File Generated : {output_file}")
