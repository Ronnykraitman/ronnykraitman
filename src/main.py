import random

import streamlit as st
import time

from resume_agent import RonnykAgent
from tools.agents_tools import display_agent_answer
from tools.custom_tools import set_custom_background

st.set_page_config(
    page_title="Ronny Kraitman",
    page_icon="🤓",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    "src/media/avatar_1.png",
    "src/media/avatar_2.png",
    "src/media/avatar_3.png",
    "src/media/avatar_4.png",
    "src/media/avatar_5.png",
    "src/media/avatar_6.png",
    "src/media/avatar_7.png",
    "src/media/avatar_8.png",
    "src/media/avatar_9.png"
]

if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = random.choice(user_avatar_options)

set_custom_background("src/media/ronnyk_background.png")

with open('style.css') as f:
    css = f.read()

ronnyk_avatar = "src//media/ronnyk_avatar.jpg"

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)


if __name__ == "__main__":
    col_1, col_2 = st.columns([3,2.5])

    st.markdown('<div class="prompt"', unsafe_allow_html=True)
    prompt = st.chat_input("Ask me anything you wanna know")
    st.markdown('</div>', unsafe_allow_html=True)

    with col_2:
        with st.container():
            st.markdown(f"""
                <div class="header-container">
                    <div class="title-container">
                        <div class="title">Hey There, I'm Ronny</div>
                        <div class="title-slogan">Senior Backend Developer</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if not st.session_state.headline:
                time.sleep(2)
                st.session_state.headline = True

        with st.container(height=400, border=None):

            for message in st.session_state.messages:
                avatar = ronnyk_avatar if message["role"] == "assistant" else st.session_state.user_avatar
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar=st.session_state.user_avatar):
                    st.markdown(prompt)

                agent_response = st.session_state.ronnyk_agent.chat(prompt)
                st.session_state.messages.append({"role": "assistant", "content": agent_response})

                with st.chat_message("assistant", avatar=ronnyk_avatar):
                    display_agent_answer(agent_response)

                st.rerun()
