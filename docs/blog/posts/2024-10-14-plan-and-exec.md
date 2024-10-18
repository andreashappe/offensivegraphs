---
authors:
    - andreashappe
    - brandl
date: 2024-10-14
categories:
    - 'initial-journey'
    - 'planning-and-decision-making'
---
# Adding Plan-and-Execute Planner

All sources can be found in [our github history](https://github.com/andreashappe/offensivegraphs/tree/dbe5ae76d044e6dc876dcb86029f853a30bac565).

When using LLMs for complex tasks like hacking, a common problem is that they become hyper-focused upon a single attack vector and ignore all others. They go down a "depth-first" rabbit hole and never leave it. This was experienced by [me](https://arxiv.org/abs/2310.11409) and [others](https://arxiv.org/abs/2308.06782).

## Plan-and-Execute Pattern

One potential solution is the ['plan-and-solve'-pattern](https://arxiv.org/abs/2305.04091) (often also named ['plan-and-execute'-pattern](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/)). in this strategy, one LLM (the `planner`) is given the task of creating a high-level task plan based upon the user-given objective. The task plan is processed by another LLM module (the `agent` or `executor`). Basically, the next step from the task plan is taken and forwarded to the executer to solve within in a limited number of steps or time.

The executor's result is passed back to another LLM module (the `replan` module) that updates the task plan with the new findings and, if the overall objective has not been achieved already, calls the executor agent with the next task step. The `replan` and `plan` LLM modules are typically very similar to each other, as we will see within our code example later.

An advanced version is Gelei's `Penetration Task Tree` [detailed in the pentestGPT paper](https://arxiv.org/abs/2308.06782).

Let's build a simple plan-and-execute prototype, highly influenced by the [plan-and-execute langgraph example](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/).

## The High-Level Graph

One benefit of using this blog for documenting our journey is that we can do the explanation in a non-linear (regarding the source code) order.

Let's start with the overall graph as defined through `create_plan_and_execute_graph`:

```python title="graphs/plan_and_execute.py: Overall graph" linenums="73"
def create_plan_and_execute_graph(llm, execute_step):

    def should_end(state: PlanExecute):
        if "response" in state and state["response"]:
            return END
        else:
            return "agent"

    def plan_step(state: PlanExecute):
        planner = planner_prompt | llm.with_structured_output(Plan)
        plan = planner.invoke({"messages": [("user", state["input"])]})
        return {"plan": plan.steps}

    def replan_step(state: PlanExecute):
        replanner = replanner_prompt | llm.with_structured_output(Act)
        output = replanner.invoke(state)
        if isinstance(output.action, Response):
            return {"response": output.action.response}
        else:
            return {"plan": output.action.steps}

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

    return workflow
```

The overall flow is defined in line 94 and following. You can see the mentioned nodes: `planner`, `agent` (the executor)and `replan` and a graph that follows the outline described in the introduction.

`should_end` (line 75) is the exit-condition: if the replanner is not calling the sub-agent (`agent`), it can only send a message to the initial human (within the field `response`). The function detects this response and subsequently exits the graph.

### Shared State

The shared state describes the data that is stored within the graph, i.e., the data that all our nodes will have access to. It is defined through `PlanExecute`:

```python title="graphs/plan_and_execute.py: Shared State" linenums="45"
class PlanExecute(TypedDict):
    input: str # the initial user-given objective
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str # response from the agent to the user
```

We store the following data:

- `input`: the initially given user question/objective, i.e., "I want to become root"
- `response`: the final answer given by our LLM to the user question
- `plan`: a (string) list of planning steps that need to be performed to hopefully solve the user question
- `past_steps`: a list of already performed planning steps. In our implementation this also contains a short summary (given by the execution agent) about the operations performed by the execution agent (stored for each past step).

## Graph Nodes/Actions

`planner` and `replan` are implemented through `plan_step` and `replan_step` respectively. The `agent` (or executor) is passed in as `execute_step` function parameter as this allows us to easily reuse the generic plan-and-execute graph for different use-cases.

### Planner

Let's look at the planner next. It is implemented as a LLM call using `llm.with_structured_output` to allow for automatic output parsing into the `Plan` data structure:

```python title="graphs/plan_and_execute.py: Plan data structure" linenums="52"
class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )
```

The output is thus a simple string list with the different future planning steps. The LLM prompt itself is defined as:

```python title="graphs/plan_and_execute.py: Planner Prompt" linenums="12"
planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.""",
        ),
        ("placeholder", "{messages}"),
    ]
)
```

This is rather generic. The initial user question will be passed in as first message within `{messages}` and that's more or less it.

### Replanner

The result of the replanner node action/step wil be following:

```python title="graphs/plan_and_execute.py: Replanner data structure" linenums="59"
class Response(BaseModel):
    """Response to user."""
    response: str

class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )
```

So it's either a user `Response` (consisting of a string) signalling that we have finished, or an updated `Plan` (the previously mentioned list of strings) which the `executor` will act upon next.

Let's look at the prompt:

```python title="graphs/plan_and_execute.py: Replanner Prompt" linenums="24"
replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.

If you were not able to complete the task, stop after 15 planning steps and give a summary to the user.
"""
)
```

The prompt's input is the initial objective (`input`), the current plan containing all future high-level task steps (`plan`), and a list of previously executed planning steps (`plan_steps`). In our implementation, each `plan_step` also contains a LLM-derived summary of the actions performed by the `executor` while trying to solve the planning step as well as it's results. This should help the `replan` agent to better update subsequent plans.

We also tell the LLM to stop after 15 high-level task steps and give a final summary to the user. If the objective has been solved before, the LLM will detect this too and auto-magically stop execution.

### Agent/Executor

The `executor` node/function is passed into our generic path as a callback function. This allows to easily modify our generic graph to solve different objectives with their respective specialized executor agents.

Let's start with our simple implementation:

```python title="plan_and_execute.py: Executor Function" linenums="29"
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
        stream_mode='values'
    )

    agent_response = None
    for event in events:
        print_event(console, event)
        agent_response = event

    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }
```

We are reusing our [initial simple agent](2024-10-10-first-steps-and-initial-version.md) as executor on line 46. On lines 29-31 we are creating a new connection to OpenAI and configure some SSH-based tools (as mentioned in the original post) for our executor agent. This fully separated the LLM connection, graph history and supported tools from the LLM-configuration used by the plan-and-execute graph and would allow for using different LLMs for the `planner` and `executor` respectively.

Starting on line 49 , we execute our sub-agent and output its steps before returning the final step on line 59 as `past_steps`. This will append our agent's output (which includes a generated summary of its results) to `past_steps` within our shared state (which will subsequently be used by the `replanner` agent to refine future planning steps).

## Wiring it up and starting it

The only thins left is to wire up everything, provide the initial template and output the occurring events (to see what our LLM agent is doing):

```python title="plan_and_execute.py: Starting our Agent" linenums="64"
workflow = create_plan_and_execute_graph(llm, execute_step)
app = workflow.compile()
print(app.get_graph(xray=True).draw_ascii())

# now start our agent and give it our initial prompt ('get root')
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)

# start everything
events = app.stream(
    input = {"input": template },
    config = {"recursion_limit": 50},
    stream_mode = "values"
)

# output all occurring logs
for event in events:
    print_event(console, event)
```

And that's it! Enjoy your multi-agent driven plan-and-execute architecture!

## Improvement Ideas

Before we move further with our exploration of offensive graphs,, we might want to investigate logging and tracing options. As we are now starting subgraphs (or might even run subgraphs/agents in-parallel), traditional console output becomes confusing to follow. Stay tuned!
