from dotenv import load_dotenv
from ssh import SshExecuteTool, SshTestCredentialsTool,get_ssh_connection_from_env 
from typing import Annotated
from typing_extensions import TypedDict
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.console import Group
from rich.markdown import Markdown

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

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
llm_with_tools = llm.bind_tools(tools)

# define our action graph
class State(TypedDict):
    notes: str
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# this is still named chatbot as we copied it from the langgraph
# example code. This should rather be named 'hackerbot' or something
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def scribe(state: State):
    if messages := state.get("messages", []):
        mission = messages[0].content
        tool_call = messages[-2].tool_calls[0]
        tool_response = messages[-1].content
    notes = state.get("notes", f"The task is {mission}")
    return {"notes": llm.invoke(f""" You are tasked with taking notes of everything we learned about this linux system in a structured way.
                                Keep your notes like a high level structured summary in markdown and prune them regularly to only keep relevant information.
                                Try to stay within 25 Lines only write about things we know.
                                Here are your current notes:
                                {notes} 
                                Here is a toolcwe called {tool_call} 
                                which gave us this output {tool_response}""").content}

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
graph_builder.add_node("scribe", scribe)
graph_builder.add_node("tools", ToolNode(tools=tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", route_tools)
#graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("tools", "scribe")
graph_builder.add_edge("scribe", "chatbot")
graph_builder.add_edge("chatbot", END)

# now instantiate the graph. We add memory, so that our LLM action
# remembers what it has executed before (as well as the reults it got)
def create_executor_graph():
    memory = MemorySaver()
    return graph_builder.compile(checkpointer=memory)

graph = create_executor_graph()
print(graph.get_graph(xray=True).draw_ascii())



import sys
sys.exit(1)

if __name__ == '__main__':
    # Initialize the console and layout
    console = Console()
    layout = Layout()

    # Split the layout into left and right panels
    layout.split_row(
        Layout(name="left"),
        Layout(name="right")
    )

    # Variables to hold the content of the left and right panels
    left_messages = []
    notes_content = ""

    # Start the agent and provide the initial prompt
    template = PromptTemplate.from_template("""
    You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

    Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
    """).format(username=conn.username, password=conn.password)

    events = graph.stream(
        input={
            "messages": [
                ("user", template),
            ]
        },
        config={
            "configurable": {"thread_id": "1"}
        },
        stream_mode="values"
    )

    # Use Live to update the layout dynamically
    with Live(layout, console=console, refresh_per_second=10):
        for event in events:
            if "notes" in event:
                # Update the notes content and the right panel
                notes_content = event["notes"]
                layout["right"].update(Panel(Markdown(notes_content), title="Notes"))

            if "messages" in event:
                message = event["messages"][-1]
                if isinstance(message, HumanMessage):
                    panel = Panel(str(message.content), title="User says")
                elif isinstance(message, ToolMessage):
                    panel = Panel(str(message.content), title=f"Tool Response from {message.name}")
                elif isinstance(message, AIMessage):
                    if message.content != '':
                        panel = Panel(str(message.content), title="AI says")
                    elif len(message.tool_calls) == 1:
                        tool = message.tool_calls[0]
                        panel = Panel(Pretty(tool["args"]), title=f"Tool Call to {tool['name']}")
                    else:
                        panel = Panel("Unknown AI message")
                        console.log(message)
                else:
                    panel = Panel("Unknown message type")
                    console.log(message)

                # Append the new panel to the list of messages
                left_messages.append(panel)

                # Optionally, limit the number of messages displayed
                if len(left_messages) > 10:
                    left_messages.pop(0)

                # Update the left panel with the new list of messages
                layout["left"].update(Panel(Group(*left_messages), title="Messages"))
            else:
                console.log("Unexpected event format")
                console.log(event)