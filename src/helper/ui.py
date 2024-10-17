from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

def get_panels_from_event(console: Console, event):
    panels = []

    if "messages" in event:
        message = event["messages"][-1]
        if isinstance(message, HumanMessage):
            panels.append(Panel(str(message.content), title="Input to the LLM"))
        elif isinstance(message, ToolMessage):
            panels.append(Panel(str(message.content), title=f"Tool Reponse from {message.name}"))
        elif isinstance(message, AIMessage):
            if message.content != '':
                panels.append(Panel(str(message.content), title="Output from the LLM"))
            elif len(message.tool_calls) >= 1:
                for tool in message.tool_calls:
                    panels.append(Panel(Pretty(tool["args"]), title=f"Tool Call to {tool["name"]}"))
            else:
                panels.append(Panel(Pretty(message), title='unknown message type'))
        else:
            raise Exception("Unknown message type: " + str(message))
    else:
        console.log("no messages in event?")
        console.log(event)
    return panels

def print_event(console: Console, event):
    panels = get_panels_from_event(console, event)

    for panel in panels:
        console.print(panel)

def print_event_stream(console: Console, events):
    for event in events:
        print_event(console, event)