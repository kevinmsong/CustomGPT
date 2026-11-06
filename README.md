# CustomGPT

Password-gated Streamlit chat UI for OpenAI (GPT-4o), with persistent JSON chat history and optional file / image analysis uploads.

## Features

- App login via password stored in Streamlit secrets (`app_password`)
- OpenAI API key from secrets (`openai_api_key`) or manual entry (validated with `models.list`)
- Chat with GPT-4o using conversation history as context
- Persist messages to `chat_history.json` (load on startup; clear with optional timestamped backup)
- Sidebar toggle for full history vs last 10 messages
- Upload and discuss files: txt, pdf, csv, json, py, md, png, jpg, jpeg (max 5MB)
- Image uploads resized/encoded and analyzed via GPT-4o vision
- PDF text via PyPDF2; CSV via pandas; logout clears auth session state

## Requirements

See `requirements.txt`:

- streamlit==1.31.0
- openai==1.12.0
- python-dotenv==1.0.0
- PyPDF2==3.0.1
- pandas==2.1.4
- requests==2.31.0
- Pillow==10.2.0

## Setup

1. Clone the repo and create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `.streamlit/secrets.toml`:

```toml
app_password = "YOUR_APP_PASSWORD"
openai_api_key = "YOUR_OPENAI_API_KEY"
```

## Usage

```bash
streamlit run customgpt.py
```

Log in with the app password, authenticate the OpenAI key, then chat or use **Analyze Files** in the sidebar.

## Notes

- Page title in-app: “OpenAI Chat Interface”.
- Clearing history renames the current history file to a `chat_history_backup_*.json` backup when messages exist.
