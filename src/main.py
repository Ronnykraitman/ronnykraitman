import random
import time
from pathlib import Path

import streamlit as st

from resume_agent import RonnykAgent
from tools.agents_tools import display_agent_answer
from tools.custom_tools import set_custom_background

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
RESUME_PDF = ROOT_DIR / "public" / "my_resume.pdf"
BG_IMAGE = SRC_DIR / "media" / "ronnyk_background.png"
STYLE_CSS = ROOT_DIR / "style.css"

st.set_page_config(
    page_title="Ronny Kraitman · Senior AI & Backend Engineer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "messages_history" not in st.session_state:
    st.session_state.messages_history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "headline" not in st.session_state:
    st.session_state.headline = False

if "ronnyk_agent" not in st.session_state:
    ronnyk_agent: RonnykAgent = RonnykAgent()
    ronnyk_agent.create_an_agent()
    st.session_state.ronnyk_agent = ronnyk_agent

user_avatar_options = [
    str(SRC_DIR / f"media/avatar_{i}.png") for i in range(1, 10)
]

if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = random.choice(user_avatar_options)

set_custom_background(str(BG_IMAGE))

if STYLE_CSS.exists():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

ronnyk_avatar = str(SRC_DIR / "media" / "ronnyk_avatar.jpg")


if __name__ == "__main__":
    col_1, col_2 = st.columns([3, 2.5])

    st.markdown('<div class="prompt">', unsafe_allow_html=True)
    prompt = st.chat_input("Ask me about AI systems, data pipelines, scale…")
    st.markdown("</div>", unsafe_allow_html=True)

    with col_2:
        with st.container():
            st.markdown(
                """
                <div class="header-container">
                    <div class="title-container">
                        <div class="title">Hey There, I'm Ronny</div>
                        <div class="title-slogan">Senior AI &amp; Backend Engineer</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not st.session_state.headline:
                time.sleep(1)
                st.session_state.headline = True

            # Download Resume Button
            if RESUME_PDF.exists():
                with open(RESUME_PDF, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                st.download_button(
                    label="📄 Download Resume (PDF)",
                    data=pdf_bytes,
                    file_name="Ronny_Kraitman_Resume.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        with st.container(height=450, border=None):
            for message in st.session_state.messages:
                avatar = (
                    ronnyk_avatar
                    if message["role"] == "assistant"
                    else st.session_state.user_avatar
                )
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

            if prompt:
                st.session_state.messages.append(
                    {"role": "user", "content": prompt}
                )
                with st.chat_message("user", avatar=st.session_state.user_avatar):
                    st.markdown(prompt)

                agent_response = st.session_state.ronnyk_agent.chat(prompt)
                st.session_state.messages.append(
                    {"role": "assistant", "content": agent_response}
                )

                with st.chat_message("assistant", avatar=ronnyk_avatar):
                    display_agent_answer(agent_response)

                st.rerun()
