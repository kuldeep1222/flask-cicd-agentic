## Build image and run test file automatically by agents


from langchain_core.tools import tool

from langchain.agents import tool, initialize_agent, AgentType

from langchain_google_genai import ChatGoogleGenerativeAI

import os

os.environ["GOOGLE_API_KEY"] = "AIzaSyBUXECZE5jSLhU2ouDR-Six9H2B0pJn4jk"

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

#Tool 1

@tool
def build_docker_image(input: str) -> str:
    """Builds Docker image from the current directory."""
    import os
    result = os.system("docker build -t flask-cicd:A1 .")
    return "Build success" if result == 0 else "Build failed"

# Tool 2
@tool
def run_pytest(input: str) -> str:
    """Runs pytest on the Flask app."""
    import os
    result = os.system("pytest test_flask_cicd.py")
    return "Tests passed" if result == 0 else "Tests failed"

tools = [ run_pytest, build_docker_image ]

agent = initialize_agent(tools, llm, verbose=True)

agent.run("run the test file and Build the Docker image ")
