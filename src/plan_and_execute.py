import asyncio
import time

from dotenv import load_dotenv
from graphs.plan_and_execute import PlanExecute

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from helper.common import get_or_fail
from tools.ssh import get_ssh_connection_from_env 
from graphs.initial_version import create_chat_tool_agent_graph

from graphs.plan_and_execute import create_plan_and_execute_graph
from initial_version import graph as executor_graph

# setup configuration from environment variables
load_dotenv()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself
conn = get_ssh_connection_from_env()

# now start our agent and give it our initial prompt ('get root')
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)

# initialize the ChatOpenAI model and register the tool (ssh connection)
llm = ChatOpenAI(model="gpt-4o", temperature=0)

async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}. Stop after 10 command executions."""
    agent_response = await executor_graph.ainvoke(
        {"messages": [("user", task_formatted)]},
        config = {
            "configurable": {"thread_id": f"thread-{time.time()}" }
        },
    )
    print("*****n\n\n\n\nresponse:" + str(agent_response["messages"][-1]))
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }

# create the graph
workflow = create_plan_and_execute_graph(llm, execute_step)
app = workflow.compile()
print(app.get_graph(xray=True).draw_ascii())

config = {"recursion_limit": 50}
inputs = {"input": template }

# start everything
async def start():
    async for event in app.astream(inputs, config=config):
        if "messages" in event:
            print("!!!! message:")
            event["messages"][-1].pretty_print()
        elif "plan" in event:
            print("!!!! plan:")
            event["plan"][-1].pretty_print()
        else:
            print("Not event!")
            for k, v in event.items():
                if k != "__end__":
                    print(v)

asyncio.run(start())