from dotenv import load_dotenv
from ssh import SshExecuteTool, SshTestCredentialsTool,get_ssh_connection_from_env 

from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from common import get_or_fail

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
    for event in events:
        if "messages" in event:
            message = event["messages"][-1]
            if isinstance(message, HumanMessage):
                console.print(Panel(str(message.content), title="Punny Human says"))
            elif isinstance(message, ToolMessage):
                console.print(Panel(str(message.content), title=f"Tool Reponse from {message.name}"))
            elif isinstance(message, AIMessage):
                if message.content != '':
                    console.print(Panel(str(message.content), title="AI says"))
                elif len(message.tool_calls) == 1:
                    tool = message.tool_calls[0]
                    console.print(Panel(Pretty(tool["args"]), title=f"Tool Call to {tool["name"]}"))
                else:
                    print("WHAT do you want?")
                    console.log(message)
            else:
                print("WHAT message are you?")
                console.log(message)
        else:
            print("WHAT ARE YOU??????")
            console.log(event)