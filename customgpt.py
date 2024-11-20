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

# Configuration
HISTORY_FILE = "chat_history.json"
ALLOWED_TYPES = ["txt", "pdf", "csv", "json", "py", "md"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_api_key(api_key):
    """Validate OpenAI API key"""
    try:
        client = openai.OpenAI(api_key=api_key)
        # Make a simple API call to validate the key
        client.models.list()
        return True
    except:
        return False

# Load chat history from JSON file
def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

# Save chat history to JSON file
def save_chat_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# Authentication function for app password
def authenticate_app(password):
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

# Chat function
def chat_with_openai(message, history):
    client = openai.OpenAI(api_key=st.session_state.openai_key)
    
    # Prepare the messages including history
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    
    # Get response from OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def openai_auth_interface():
    """Handle OpenAI authentication interface"""
    st.sidebar.header("OpenAI Authentication")
    
    # Option to use API key from secrets
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
        # Manual API key entry
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

# Main app
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
                    st.session_state.messages.append({
                        "role": "user",
                        "content": file_prompt,
                        "timestamp": datetime.now().isoformat()
                    })
                    save_chat_history(st.session_state.messages)
                    st.experimental_rerun()
        
        # Display uploaded files
        if st.session_state.uploaded_files:
            st.write("Uploaded files:")
            for file in st.session_state.uploaded_files:
                st.write(f"- {file}")
        
        # Logout and Clear History buttons
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.openai_key = None
            st.experimental_rerun()
        
        if st.button("Clear History"):
            st.session_state.messages = []
            st.session_state.uploaded_files = []
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            st.experimental_rerun()
    
    # Load chat history
    if not st.session_state.messages:
        st.session_state.messages = load_chat_history()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What's on your mind?"):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            response, error = chat_with_openai(prompt, st.session_state.messages)
            if error:
                st.error(f"Error: {error}")
            else:
                st.write(response)
                # Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Save updated history
        save_chat_history(st.session_state.messages)

if __name__ == "__main__":
    main()
