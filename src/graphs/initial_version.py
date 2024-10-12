from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

class State(TypedDict):
    messages: Annotated[list, add_messages]

# Copied from the quickstart example, might be simplified
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

def create_chat_tool_agent_graph(llm_with_tools, tools):
    graph_builder = StateGraph(State)

    # this is still named chatbot as we copied it from the langgraph
    # example code. This should rather be named 'hackerbot' or something
    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", route_tools)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge("chatbot", END)

    return graph_builder