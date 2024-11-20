import streamlit as st
import openai
import json
import os
from datetime import datetime
import requests
from PIL import Image
import io
import base64

# Page config# Page config
st.set_page_config(
    page_title="OpenAI Chat Interface",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = None
if 'show_full_history' not in st.session_state:
    st.session_state.show_full_history = True
if 'history_loaded' not in st.session_state:
    st.session_state.history_loaded = False

# Configuration
HISTORY_FILE = "chat_history.json"
ALLOWED_TYPES = ["txt", "pdf", "csv", "json", "py", "md", "png", "jpg", "jpeg"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_SIZE = (1024, 1024)  # Maximum dimensions for images

def process_image(uploaded_file):
    """Process uploaded image file"""
    try:
        image_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(image_bytes))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if needed
        ratio = min(MAX_IMAGE_SIZE[0] / image.size[0], MAX_IMAGE_SIZE[1] / image.size[1])
        if ratio < 1:
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.LANCZOS)
        
        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def authenticate_app(password):
    """Authentication function for app password"""
    try:
        return password == st.secrets["app_password"]
    except Exception as e:
        st.error(f"Error accessing secrets: {str(e)}")
        return False

def validate_api_key(api_key):
    """Validate OpenAI API key"""
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return True
    except:
        return False

def load_chat_history():
    """Load chat history from JSON file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Error loading chat history: {str(e)}")
        return []

def save_chat_history(history):
    """Save chat history to JSON file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        st.error(f"Error saving chat history: {str(e)}")

def process_file(uploaded_file):
    """Process uploaded file and return its content"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension not in ALLOWED_TYPES:
            return None, f"File type .{file_extension} is not supported"
        
        if uploaded_file.size > MAX_FILE_SIZE:
            return None, "File is too large (max 5MB)"
        
        if file_extension in ['png', 'jpg', 'jpeg']:
            return process_image(uploaded_file), None
        
        # Handle text-based files
        if file_extension in ['txt', 'py', 'md']:
            return uploaded_file.getvalue().decode('utf-8'), None
        elif file_extension == 'pdf':
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                return content, None
            except Exception as e:
                return None, f"Error processing PDF: {str(e)}"
        elif file_extension == 'csv':
            try:
                import pandas as pd
                df = pd.read_csv(uploaded_file)
                return df.to_string(), None
            except Exception as e:
                return None, f"Error processing CSV: {str(e)}"
        elif file_extension == 'json':
            try:
                content = json.loads(uploaded_file.getvalue())
                return json.dumps(content, indent=2), None
            except Exception as e:
                return None, f"Error processing JSON: {str(e)}"
        
        return None, "Unsupported file type"
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def chat_with_openai(message, history):
    """Chat function using OpenAI API"""
    try:
        client = openai.OpenAI(api_key=st.session_state.openai_key)
        messages = [{"role": "system", "content": "You are a helpful assistant with perfect memory of the conversation history."}]
        messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in history])
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def chat_with_openai_vision(prompt, image_base64, history):
    """Chat function for image analysis"""
    try:
        client = openai.OpenAI(api_key=st.session_state.openai_key)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=500,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def openai_auth_interface():
    """Handle OpenAI API key authentication"""
    st.header("OpenAI API Authentication")
    
    auth_method = st.radio(
        "Choose authentication method:",
        ["Use API Key from Secrets", "Enter API Key Manually"]
    )
    
    if auth_method == "Use API Key from Secrets":
        try:
            api_key = st.secrets["openai_api_key"]
            if validate_api_key(api_key):
                st.session_state.openai_key = api_key
                st.success("✅ Successfully loaded API key from secrets!")
                return True
            else:
                st.error("❌ API key in secrets is invalid")
                return False
        except Exception as e:
            st.error("❌ No API key found in secrets or key is invalid")
            return False
    else:
        with st.form("api_key_form"):
            api_key = st.text_input("Enter your OpenAI API key:", type="password")
            submitted = st.form_submit_button("Submit")
            if submitted:
                if validate_api_key(api_key):
                    st.session_state.openai_key = api_key
                    st.success("✅ API key validated successfully!")
                    return True
                else:
                    st.error("❌ Invalid API key!")
                    return False
    return False

# [Previous imports and configurations remain the same...]

# Initialize session state variables if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = None
if 'show_full_history' not in st.session_state:
    st.session_state.show_full_history = True
if 'history_loaded' not in st.session_state:
    st.session_state.history_loaded = False

# [Previous functions remain the same until main()]

def main():
    st.set_page_config(
        page_title="OpenAI Chat Interface",
        page_icon="🤖",
        layout="wide"
    )
    
    # Hide Streamlit branding
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    st.title("🤖 OpenAI Chat Interface")
    
    # Load history at startup if not already loaded
    if not st.session_state.history_loaded:
        st.session_state.messages = load_chat_history()
        st.session_state.history_loaded = True
    
    # App Authentication
    if not st.session_state.authenticated:
        with st.form("login_form"):
            password = st.text_input("Enter app password:", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if authenticate_app(password):
                    st.session_state.authenticated = True
                    st.experimental_rerun()
                else:
                    st.error("Incorrect password!")
        return

    # OpenAI API Key Authentication
    if not st.session_state.openai_key:
        if not openai_auth_interface():
            return

    # Main Interface with sidebar
    with st.sidebar:
        st.header("Settings")
        show_history = st.checkbox("Show Full History", value=st.session_state.show_full_history)
        st.session_state.show_full_history = show_history
        
        st.header("File Upload")
        uploaded_files = st.file_uploader(
            "Upload files to discuss",
            type=ALLOWED_TYPES,
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("Analyze Files", use_container_width=True):
                for uploaded_file in uploaded_files:
                    if uploaded_file.type.startswith('image/'):
                        st.image(uploaded_file, caption=uploaded_file.name)
                        img_base64 = process_image(uploaded_file)
                        if img_base64:
                            response, error = chat_with_openai_vision(
                                f"Please analyze this image: {uploaded_file.name}",
                                img_base64,
                                st.session_state.messages
                            )
                            if error:
                                st.error(error)
                            else:
                                new_message = {
                                    "role": "assistant",
                                    "content": response,
                                    "timestamp": datetime.now().isoformat()
                                }
                                st.session_state.messages.append(new_message)
                                save_chat_history(st.session_state.messages)
                    else:
                        content, error = process_file(uploaded_file)
                        if error:
                            st.error(error)
                        else:
                            new_message = {
                                "role": "user",
                                "content": f"Analyzing file: {uploaded_file.name}\n\n{content}",
                                "timestamp": datetime.now().isoformat()
                            }
                            st.session_state.messages.append(new_message)
                            save_chat_history(st.session_state.messages)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Display", use_container_width=True):
                st.session_state.show_full_history = False
                st.experimental_rerun()
            
            if st.button("Clear History", use_container_width=True):
                if st.session_state.messages:
                    backup_file = f"chat_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    save_chat_history(st.session_state.messages)
                    os.rename(HISTORY_FILE, backup_file)
                    st.session_state.messages = []
                    save_chat_history([])
                    st.info(f"History cleared! Backup saved as {backup_file}")
                    st.experimental_rerun()
        
        with col2:
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.openai_key = None
                st.experimental_rerun()
    
    # Main chat container
    chat_container = st.container()
    
    # Empty space to push chat input to bottom
    st.markdown("<br>" * 20, unsafe_allow_html=True)
    
    # Chat input at bottom
    input_container = st.container()
    with input_container:
        prompt = st.chat_input("What would you like to discuss?")
    
    # Display messages in chat container
    with chat_container:
        messages_to_show = (
            st.session_state.messages if st.session_state.show_full_history 
            else st.session_state.messages[-10:] if st.session_state.messages 
            else []
        )
        
        for message in messages_to_show:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "timestamp" in message:
                    st.caption(f"Time: {message['timestamp']}")
    
    # Handle new messages
    if prompt:
        # Add user message
        new_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.messages.append(new_message)
        save_chat_history(st.session_state.messages)
        
        # Get assistant response
        with st.chat_message("assistant"):
            response, error = chat_with_openai(prompt, st.session_state.messages)
            if error:
                st.error(error)
            else:
                st.write(response)
                assistant_message = {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.messages.append(assistant_message)
                save_chat_history(st.session_state.messages)
        
        # Rerun to update the chat display
        st.experimental_rerun()

if __name__ == "__main__":
    main()
