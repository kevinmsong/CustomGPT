import streamlit as st
import openai
import json
import os
from datetime import datetime

# Initialize session state variables if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Configuration
HISTORY_FILE = "chat_history.json"

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

# Authentication function
def authenticate(password):
    return password == st.secrets["app_password"]

# Chat function
def chat_with_openai(message, history):
    client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
    
    # Prepare the messages including history
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    
    # Get response from OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1,
    )
    
    return response.choices[0].message.content

# Main app
def main():
    st.title("🤖 OpenAI Chat Interface")
    
    # Authentication
    if not st.session_state.authenticated:
        password = st.text_input("Enter password:", type="password")
        if st.button("Login"):
            if authenticate(password):
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Incorrect password!")
        return
    
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
            response = chat_with_openai(prompt, st.session_state.messages)
            st.write(response)
        
        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save updated history
        save_chat_history(st.session_state.messages)
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()
    
    # Clear history button
    if st.sidebar.button("Clear History"):
        st.session_state.messages = []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.experimental_rerun()

if __name__ == "__main__":
    main()