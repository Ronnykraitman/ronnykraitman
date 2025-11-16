import base64
import streamlit as st
from pypdf import PdfReader

def set_custom_background(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()
    background_css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: left center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(background_css, unsafe_allow_html=True)

def get_resume_summary(path):
    with open(path, "r", encoding="utf-8") as f:
        summary = f.read()
        return summary

def get_full_resume(path):
    reader = PdfReader(path)
    resume = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            resume += text
    return resume