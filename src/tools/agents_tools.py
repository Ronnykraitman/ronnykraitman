import streamlit as st
import time
from agents import function_tool

def display_agent_answer(response_text):
    full_response = ""
    message_placeholder = st.empty()
    for chunk in response_text.split():
        full_response += chunk + " "
        time.sleep(0.07)
        message_placeholder.markdown(full_response + "▌")

    message_placeholder.markdown(f'<div style="text-align:left;"><div class="assistant-msg">{full_response}</div></div>', unsafe_allow_html=True)

@function_tool
def open_pdf_in_new_tab():
    """Return a command telling the UI to open a PDF in a new browser tab if the user asked to see or download the resume / cv"""
    return {
        "action": "show_link",
        "url": "../static/my_resume.pdf",
        "text": "Check out my resume"
    }