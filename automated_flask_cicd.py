import os
import time
import requests
from github import Github
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import tool, initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI

# Load secrets from id_pass.env
load_dotenv(dotenv_path="id_pass.env")

# Set environment variables
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_PASS = os.getenv("JENKINS_PASS")
REPO_NAME = "flask-cicd-agentic"
JENKINS_URL = "http://localhost:8080"

# Load LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


@tool
def create_github_repo(input: str) -> str:
    """Creates GitHub repo and pushes code without .env"""
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo = user.create_repo(REPO_NAME)

    with open(".gitignore", "a+") as f:
        f.seek(0)
        if "id_pass.env" not in f.read():
            f.write("\nid_pass.env\n")

    os.system("rm -rf .git")
    os.system("git init")
    os.system("git branch -M main")
    os.system(f"git remote add origin git@github.com:{GITHUB_USERNAME}/{REPO_NAME}.git")
    os.system("git add .")
    os.system("git commit -m 'Initial automated commit'")
    os.system("git push -u origin main")

    return f"GitHub repo pushed: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}"


@tool
def start_jenkins(input: str) -> str:
    """Starts Jenkins service and disables the firewall"""
    try:
        os.system("systemctl start jenkins")
        os.system("systemctl stop firewalld")
        return " Jenkins started and firewall stopped."
    except Exception as e:
        return f" Failed to start Jenkins or stop firewall: {str(e)}"


def wait_for_jenkins_build(job_name, jenkins_url, auth, max_wait=300, poll_interval=5):
    build_url = f"{jenkins_url}/job/{job_name}/lastBuild/api/json"
    console_url = f"{jenkins_url}/job/{job_name}/lastBuild/consoleText"
    elapsed = 0

    while elapsed < max_wait:
        try:
            r = requests.get(build_url, auth=auth)
            if r.status_code == 200:
                data = r.json()
                if not data.get("building", True):
                    output = requests.get(console_url, auth=auth).text
                    # Extract curl response line
                    curl_output = ""
                    for line in output.splitlines():
                        if "curl" in line.lower():
                            continue  # skip command itself
                        if "Hello" in line or "{" in line or "}" in line or "200 OK" in line:
                            curl_output = line.strip()
                    result = data.get("result")
                    return (result == "SUCCESS", curl_output or "⚠️ Curl response not captured.")
        except Exception as e:
            return (False, f" Error checking Jenkins build: {str(e)}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    return (False, " Build timed out after waiting.")

@tool
def create_jenkins_job(input: str) -> str:
    """Creates Jenkins job with CSRF crumb and triggers build. Cleans old containers/images."""
    job_name = "Flask_CICD_Agentic"
    repo_url = f"git@github.com:{GITHUB_USERNAME}/{REPO_NAME}.git"

    try:
        # Clean previous containers/images
        os.system("docker rm -f $(docker ps -aq) > /dev/null 2>&1")
        os.system("docker rmi -f $(docker images -q flask-cicd:agentic) > /dev/null 2>&1")

        crumb_response = requests.get(
            f"{JENKINS_URL}/crumbIssuer/api/json",
            auth=(JENKINS_USER, JENKINS_PASS)
        )
        crumb_response.raise_for_status()
        crumb_data = crumb_response.json()
        crumb = crumb_data['crumb']
        crumb_field = crumb_data['crumbRequestField']

        config_xml = f"""<project>
  <actions/>
  <description>LangChain Agentic CI/CD Job</description>
  <scm class=\"hudson.plugins.git.GitSCM\" plugin=\"git@4.4.5\">
    <configVersion>2</configVersion>
    <userRemoteConfigs>
      <hudson.plugins.git.UserRemoteConfig>
        <url>{repo_url}</url>
      </hudson.plugins.git.UserRemoteConfig>
    </userRemoteConfigs>
    <branches>
      <hudson.plugins.git.BranchSpec>
        <name>*/main</name>
      </hudson.plugins.git.BranchSpec>
    </branches>
  </scm>
  <builders>
    <hudson.tasks.Shell>
      <command>#!/bin/bash
sudo pytest test_flask_cicd.py
sudo docker build -t flask-cicd:agentic .
sudo docker run -d -p 5000:5000 flask-cicd:agentic
sleep 5
sudo curl http://localhost:5000/info</command>
    </hudson.tasks.Shell>
  </builders>
</project>"""

        headers = {
            "Content-Type": "application/xml",
            crumb_field: crumb
        }

        response = requests.post(
            f"{JENKINS_URL}/createItem?name={job_name}",
            headers=headers,
            data=config_xml,
            auth=(JENKINS_USER, JENKINS_PASS)
        )

        if response.status_code == 200:
            build_trigger = requests.post(
                f"{JENKINS_URL}/job/{job_name}/build",
                auth=(JENKINS_USER, JENKINS_PASS),
                headers={crumb_field: crumb}
            )
            if build_trigger.status_code in [200, 201]:
                msg = f" Jenkins job '{job_name}' created and build triggered. Waiting for result..."
                success, output = wait_for_jenkins_build(job_name, JENKINS_URL, (JENKINS_USER, JENKINS_PASS))
                if success:
                    return msg + "\n\n Build successful. Curl response:\n" + output
                else:
                    return msg + "\n\n Build failed. Reason:\n" + output
            else:
                return f"⚠️ Job created, but failed to trigger build: {build_trigger.status_code}\n{build_trigger.text}"

        elif response.status_code == 400 and "already exists" in response.text.lower():
            return f"⚠️ Jenkins job '{job_name}' already exists."
        else:
            return f" Failed to create Jenkins job: {response.status_code}\n{response.text}"

    except Exception as e:
        return f" Exception while creating or triggering Jenkins job: {str(e)}"


# Register tools
tools = [
    create_github_repo,
    start_jenkins,
    create_jenkins_job,
]

# Initialize Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Run the chain
agent.run("Create GitHub repo and push code, start Jenkins, create job to test and run Flask app with curl")

