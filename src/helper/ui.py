from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

def print_event(console: Console, event):
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

def print_event_stream(console: Console, events):
    for event in events:
        print_event(console, event)