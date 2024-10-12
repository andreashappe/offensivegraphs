from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from rich.console import Console

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

# define our action graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# this is still named chatbot as we copied it from the langgraph
# example code. This should rather be named 'hackerbot' or something
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def route_tools(state: State):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", route_tools)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("chatbot", END)

# now instantiate the graph. We add memory, so that our LLM action
# remembers what it has executed before (as well as the reults it got)
def create_executor_graph():
    return graph_builder.compile()

graph = create_executor_graph()

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
        config = {
            "configurable": {"thread_id": "1"}
        },
        stream_mode="values"
    )

    # output all the events that we're getting from the agent
    print_event_stream(console, events)