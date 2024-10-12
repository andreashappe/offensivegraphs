from dotenv import load_dotenv
from ssh import SshExecuteTool, SshTestCredentialsTool,get_ssh_connection_from_env 

from rich.console import Console

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from common import get_or_fail
from ui import print_event_stream

# setup configuration from environment variables
load_dotenv()
conn = get_ssh_connection_from_env()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself

# connect to the target system over SSH
conn.connect()

# initialize the ChatOpenAI model and register the tool (ssh connection)
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [SshExecuteTool(conn), SshTestCredentialsTool(conn)]

# configure our agent
agent_executor = create_react_agent(llm, tools)

# now start our agent and give it our initial prompt ('get root')
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)

if __name__ == '__main__':

    console = Console()

    events = agent_executor.stream(
        {
            "messages": [
                ("user", template),
            ]
        },
        stream_mode="values",
    )

    # output all the events that we're getting from the agent
    print_event_stream(console, events)