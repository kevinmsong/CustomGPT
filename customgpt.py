import streamlit as st
import openai
import json
import os
from datetime import datetime
import requests

# Initialize session state variables if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = None
if 'show_full_history' not in st.session_state:
    st.session_state.show_full_history = True

# Configuration
HISTORY_FILE = "chat_history.json"
ALLOWED_TYPES = ["txt", "pdf", "csv", "json", "py", "md"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

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
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(history):
    """Save chat history to JSON file"""
    if not os.path.exists(os.path.dirname(HISTORY_FILE)):
        os.makedirs(os.path.dirname(HISTORY_FILE))
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def get_full_context():
    """Get full chat history for context"""
    return load_chat_history()

def authenticate_app(password):
    """Authentication function for app password"""
    return password == st.secrets["app_password"]

def process_file(uploaded_file):
    """Process uploaded file and return its content"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension not in ALLOWED_TYPES:
            return None, f"File type .{file_extension} is not supported"
        
        if uploaded_file.size > MAX_FILE_SIZE:
            return None, "File is too large (max 5MB)"
        
        # Read different file types
        if file_extension == 'txt' or file_extension == 'py' or file_extension == 'md':
            content = uploaded_file.getvalue().decode('utf-8')
        elif file_extension == 'pdf':
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            except Exception as e:
                return None, f"Error processing PDF: {str(e)}"
        elif file_extension == 'csv':
            try:
                import pandas as pd
                df = pd.read_csv(uploaded_file)
                content = df.to_string()
            except Exception as e:
                return None, f"Error processing CSV: {str(e)}"
        elif file_extension == 'json':
            try:
                content = json.loads(uploaded_file.getvalue())
                content = json.dumps(content, indent=2)
            except Exception as e:
                return None, f"Error processing JSON: {str(e)}"
        
        return content, None
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def chat_with_openai(message, visible_history):
    """Chat function that uses full history for context"""
    client = openai.OpenAI(api_key=st.session_state.openai_key)
    
    # Get full history for context
    full_history = get_full_context()
    
    # Prepare the messages including full history
    messages = []
    for msg in full_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def openai_auth_interface():
    """Handle OpenAI authentication interface"""
    st.sidebar.header("OpenAI Authentication")
    
    use_secrets_key = st.sidebar.checkbox("Use API key from secrets")
    
    if use_secrets_key:
        try:
            api_key = st.secrets["openai_api_key"]
            if validate_api_key(api_key):
                st.session_state.openai_key = api_key
                st.sidebar.success("Using API key from secrets!")
                return True
            else:
                st.sidebar.error("API key from secrets is invalid!")
                return False
        except Exception as e:
            st.sidebar.error("No API key found in secrets or key is invalid.")
            return False
    else:
        api_key = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
        if st.sidebar.button("Validate API Key"):
            if validate_api_key(api_key):
                st.session_state.openai_key = api_key
                st.sidebar.success("API key validated successfully!")
                return True
            else:
                st.sidebar.error("Invalid API key!")
                return False
    
    return False

def main():
    st.title("🤖 OpenAI Chat Interface")
    
    # App Authentication
    if not st.session_state.authenticated:
        password = st.text_input("Enter app password:", type="password")
        if st.button("Login"):
            if authenticate_app(password):
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Incorrect password!")
        return
    
    # OpenAI Authentication
    if not st.session_state.openai_key:
        if not openai_auth_interface():
            return
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        
        # Toggle for showing full history
        st.session_state.show_full_history = st.checkbox(
            "Show Full History", 
            value=st.session_state.show_full_history
        )
        
        # File Upload Section
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            "Upload a file to discuss",
            type=ALLOWED_TYPES,
            help=f"Supported file types: {', '.join(ALLOWED_TYPES)}"
        )
        
        if uploaded_file:
            content, error = process_file(uploaded_file)
            if error:
                st.error(error)
            else:
                if st.button("Discuss this file"):
                    file_prompt = f"I've uploaded a file named '{uploaded_file.name}'. Here's its content:\n\n{content}\n\nPlease analyze this content and provide your insights."
                    # Add to session messages and save to history
                    new_message = {
                        "role": "user",
                        "content": file_prompt,
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.messages.append(new_message)
                    full_history = load_chat_history()
                    full_history.append(new_message)
                    save_chat_history(full_history)
                    st.experimental_rerun()
        
        # Control buttons
        if st.button("Clear Display"):
            st.session_state.messages = []
            st.experimental_rerun()
            
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.openai_key = None
            st.session_state.messages = []
            st.experimental_rerun()
    
    # Chat interface
    if st.session_state.show_full_history:
        display_messages = load_chat_history()
    else:
        display_messages = st.session_state.messages
    
    # Display chat messages
    for message in display_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What's on your mind?"):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Create new message
        new_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to session messages
        st.session_state.messages.append(new_message)
        
        # Add to full history
        full_history = load_chat_history()
        full_history.append(new_message)
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            response, error = chat_with_openai(prompt, st.session_state.messages)
            if error:
                st.error(f"Error: {error}")
            else:
                st.write(response)
                # Create assistant message
                assistant_message = {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                }
                # Add to session messages and full history
                st.session_state.messages.append(assistant_message)
                full_history.append(assistant_message)
        
        # Save updated history
        save_chat_history(full_history)

if __name__ == "__main__":
    main()
