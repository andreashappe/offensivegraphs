import asyncio
import time

from dotenv import load_dotenv
from planner_and_execute_linear import Response, get_planner_graph, get_replanner_graph, PlanExecute
from ssh import get_ssh_connection_from_env 

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from common import get_or_fail
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

planner = get_planner_graph(llm)
replanner = get_replanner_graph(llm)

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

async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}

async def replan_step(state: PlanExecute):
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}

def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"

# TODO: maybe we should rename PlanExecute to TaskPlan or something similar
workflow = StateGraph(PlanExecute)

# Add the nodes
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

# set the start node
workflow.add_edge(START, "planner")

# configure links between nodes
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end)

# create the graph
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