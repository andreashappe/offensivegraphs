import time

from dotenv import load_dotenv
from graphs.plan_and_execute import PlanExecute
from rich.console import Console

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from helper.common import get_or_fail
from helper.ui import print_event
from tools.ssh import get_ssh_connection_from_env, SshTestCredentialsTool, SshExecuteTool
from graphs.initial_version import create_chat_tool_agent_graph

from graphs.plan_and_execute import create_plan_and_execute_graph

# setup configuration from environment variables
load_dotenv()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself
conn = get_ssh_connection_from_env()
conn.connect()

# prepare console
console = Console()

# initialize the ChatOpenAI model and register the tool (ssh connection)
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# configure a second LLM connection for the exeuctor_step
llm2 = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [SshExecuteTool(conn), SshTestCredentialsTool(conn)]
llm2_with_tools = llm2.bind_tools(tools)

def execute_step(state: PlanExecute):
    plan = state["plan"]
    task = plan[0]

    template = PromptTemplate.from_template("""
    You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.
    
    To achieve this, focus upon {task}

    Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message. Stop after 10 executions. If not successful until then, give a summary of gathered facts.
    """).format(username=conn.username, password=conn.password,task=plan[0])

    # create our simple graph
    graph_builder = create_chat_tool_agent_graph(llm2_with_tools, tools)
    graph = graph_builder.compile()

    events = graph.stream(
        {"messages": [("user", template)]},
        config = {
            "configurable": {"thread_id": f"thread-{time.time()}" }
        },
        stream_mode='values'
    )

    agent_response = None
    for event in events:
        print_event(console, event)
        agent_response = event

    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }

# create the graph
workflow = create_plan_and_execute_graph(llm, execute_step)
app = workflow.compile()
print(app.get_graph(xray=True).draw_ascii())

config = {"recursion_limit": 50}
inputs = {"input": template }

# now start our agent and give it our initial prompt ('get root')
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)

# start everything
for event in app.stream(inputs, config=config, stream_mode="values"):
    print_event(console, event)