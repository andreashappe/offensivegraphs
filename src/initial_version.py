from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from rich.console import Console

from graphs.initial_version import create_chat_tool_agent_graph
from helper.common import get_or_fail
from helper.ui import print_event_stream
from tools.ssh import SshExecuteTool, SshTestCredentialsTool,get_ssh_connection_from_env 

# setup configuration from environment variables
load_dotenv()
conn = get_ssh_connection_from_env()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself

# connect to the target system over SSH
conn.connect()

# initialize the ChatOpenAI model and register the tool (ssh connection)
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [SshExecuteTool(conn), SshTestCredentialsTool(conn)]
llm_with_tools = llm.bind_tools(tools)

# create our simple graph
graph_builder = create_chat_tool_agent_graph(llm_with_tools, tools)
graph = graph_builder.compile()

if __name__ == '__main__':
    # try to make the output a bit prettier
    console = Console()

    # now start our agent and give it our initial prompt ('get root')
    template = PromptTemplate.from_template("""
    You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

    Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
    """).format(username=conn.username, password=conn.password)

    events = graph.stream(
        input = {
            "messages": [
                ("user", template),
            ]
        },
        stream_mode="values"
    )

    # output all the events that we're getting from the agent
    print_event_stream(console, events)