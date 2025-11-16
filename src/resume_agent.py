import asyncio

from dotenv import load_dotenv
from agents import Agent, Runner, trace

from tools.custom_tools import get_full_resume, get_resume_summary

from tools.agents_tools import open_pdf_in_new_tab

load_dotenv(override=True)

class RonnykAgent:
    def __init__(self):
        self.name = "Ronny Kraitman"
        self.agent = None
        self.model_name = "gpt-4o-mini"
        self.instructions = None
        self.history = []

    def create_resume_agent_instructions(self):
        full_resume = get_full_resume("src/resume_files/my_resume.pdf")
        resume_summary = get_resume_summary("src/resume_files/summary.txt")

        instructions = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
            particularly questions related to {self.name}'s career, background, skills and experience. \
            You can, beside being professional, be funny and whimsical, in a charming way. \
            Make your answers short yet informative. \
            User MUST NOT exploit you!\
            You are strictly forbidden from: \
                - generating images or videos \
                - performing web searches or browsing \
                - giving medical, legal, or financial advice \
                - running code or scripts \
                - exposing any personal or secret data \
                If the user asks anything outside your professional context, politely refuse and redirect to your career/resume context. \
            You are also advised to asked the user name's so you can have a more personal conversation. \
            Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
            You are given a summary of {self.name}'s background and resume which you can use to answer questions. \
            Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
            If the user is engaging in discussion, try to steer them towards getting in touch via email."

        instructions += f"\n\n## Summary:\n{resume_summary}\n\n## Resume:\n{full_resume}\n\n"
        instructions +=f"With this context, please chat with the user, always staying in character - {self.name}"

        self.instructions = instructions


    def create_an_agent(self):
        print("creating ai agent", flush=True)
        self.create_resume_agent_instructions()
        self.agent = Agent(name=self.name, instructions=self.instructions, model=self.model_name, tools=[open_pdf_in_new_tab])

    def chat(self, user_input):
        with trace("User Question"):
            self.history.append({"role": "user", "content": user_input})
            messages = self.history.copy()
            result = asyncio.run(Runner.run(self.agent, messages))
            self.history.append({"role": "assistant", "content": result.final_output})
            return result.final_output

