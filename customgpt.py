import streamlit as st
import openai
import json
import os
from datetime import datetime
import requests
import base64
from PIL import Image
import io

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
        # Read the image
        image_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if needed
        image = resize_image(image, MAX_IMAGE_SIZE)
        
        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    except Exception as e:
        return None, f"Error processing image: {str(e)}"

def resize_image(image, max_size):
    """Resize image while maintaining aspect ratio"""
    ratio = min(max_size[0] / image.size[0], max_size[1] / image.size[1])
    if ratio < 1:
        new_size = tuple(int(dim * ratio) for dim in image.size)
        return image.resize(new_size, Image.LANCZOS)
    return image

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

def chat_with_openai(message, history):
    """Chat function that uses full history for context"""
    client = openai.OpenAI(api_key=st.session_state.openai_key)
    
    # Include system message about persistence
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant with perfect memory of our conversation history. When asked about previous messages or context, refer to the chat history to provide accurate responses about what was discussed."
        }
    ]
    
    # Add all history
    messages.extend([
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
    ])
    
    # Add current message
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

def chat_with_openai_vision(prompt, image_base64, history):
    """Chat function that handles image analysis"""
    client = openai.OpenAI(api_key=st.session_state.openai_key)
    
    # Prepare the messages
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant capable of analyzing images and maintaining conversation history. When analyzing images, be detailed yet concise."
        }
    ]
    
    # Add history
    messages.extend([
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if not isinstance(msg["content"], dict)  # Skip previous image messages
    ])
    
    # Add image analysis request
    messages.append({
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
    })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=500,
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
    
    # Load history at startup if not already loaded
    if not st.session_state.history_loaded:
        st.session_state.messages = load_chat_history()
        st.session_state.history_loaded = True
    
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
        st.header("Settings")st.header("Settings")
        
        # Toggle for showing full history
        st.session_state.show_full_history = st.checkbox(
            "Show Full History", 
            value=st.session_state.show_full_history
        )
        
        # File Upload Section
        st.header("File Upload")
        uploaded_files = st.file_uploader(
            "Upload files to discuss",
            type=ALLOWED_TYPES,
            accept_multiple_files=True,
            help=f"Supported file types: {', '.join(ALLOWED_TYPES)}"
        )
        
        if uploaded_files:
            analyze_type = st.radio(
                "Analysis type:",
                ["Individual", "Comparative"],
                disabled=len(uploaded_files) == 1
            )
            
            if st.button("Analyze Files"):
                # Handle image files
                image_files = [f for f in uploaded_files if f.type.lower().startswith('image/')]
                other_files = [f for f in uploaded_files if not f.type.lower().startswith('image/')]
                
                if image_files:
                    with st.spinner("Processing images..."):
                        # Display images
                        if analyze_type == "Comparative" and len(image_files) > 1:
                            cols = st.columns(min(len(image_files), 3))
                            for idx, image_file in enumerate(image_files):
                                cols[idx % 3].image(image_file, use_column_width=True)
                            
                            # Process all images
                            image_base64_list = []
                            for img_file in image_files:
                                img_base64 = process_image(img_file)
                                image_base64_list.append(img_base64)
                            
                            # Create comparative analysis prompt
                            file_names = [img.name for img in image_files]
                            prompt = f"Please analyze and compare these {len(image_files)} images: {', '.join(file_names)}. Focus on key similarities and differences."
                            
                            # Process each image individually
                            for idx, (img_file, img_base64) in enumerate(zip(image_files, image_base64_list)):
                                response, error = chat_with_openai_vision(
                                    f"This is image {idx + 1} of {len(image_files)}: {img_file.name}. Ple
