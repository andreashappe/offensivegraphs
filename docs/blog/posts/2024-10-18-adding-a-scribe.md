---
authors:
    - andreashappe
    - brandl
date: 2024-10-18
categories:
    - 'initial-journey'
    - 'planning-and-decision-making'
---

# The Journey to Adding a Scribe

As our plan-and-execute architecture evolved, we encountered a pivotal challenge: managing the ever-growing context within our Language Learning Models (LLMs). 

Initially, our system thrived on a straightforward workflow, but as tasks became more complex, we need a way to efficiently handle and retain crucial information without overwhelming the LLMs (or us humans in the loop). This is where the **Scribe** node comes in, marking a significant milestone in our project's journey.

### Why We Added a Scribe Node to Take Notes

In our initial setup, the planner and executor nodes worked together to formulate and execute plans based on a rather simple feedback loop. However, as the complexity of tasks increased, the need for a systematic way to capture and store and condense information became evident. 

The **Scribe** node was introduced to address this very need. By automatically taking notes of every significant step and interaction, the Scribe ensures that valuable information is preserved throughout the execution process. This not only provides a clear high level transcript but also serves as a reliable reference for future planning and decision-making.

### Reducing Context Size for LLMs: Why It Matters

LLMs, while powerful, have inherent limitations in terms of context length. Feeding them with excessively large contexts can lead to diminished performance, increased latency, and higher computational costs. By integrating the Scribe node, we strategically harvest essential information from the active context to a structured note. This reduction in context size ensures that the LLMs operate within their optimal parameters, maintaining efficiency and accuracy. Moreover, it prevents the model from getting bogged down by redundant or irrelevant information, allowing it to focus on what's truly important.

### Step-by-Step Guide to Implementing the Scribe Node

Integrating the Scribe node into our existing architecture involves a series of methodical steps. Below is a comprehensive guide to help you navigate this integration seamlessly.

#### 1. **Understanding the Scribe's Role**

Before diving into the implementation, it's crucial to grasp the Scribe's responsibilities:

- **Note-Taking:** Automatically record significant events, tool responses, and decisions made by the executor.
- **Context Management:** Store notes in a structured format to reduce the active context size for the LLMs.
- **Facilitating Replanning:** Provide the Replanner node with accurate and concise information to refine future plans.

#### 2. **Implementing the Scribe Function**

The core of the Scribe node lies in its ability to process and store notes effectively. Here's how it's implemented in `executor_and_scribe.py`:

```python
class State(TypedDict):
    notes: str
    messages: Annotated[list, add_messages]
```
First we define a new State that includes a `notes` field. This is where the scribe will store our notes.

```python
def scribe(state: State):
    if messages := state.get("messages", []):
        mission = messages[0].content
        tool_call = messages[-2].tool_calls[0]
        tool_response = messages[-1].content
    notes = state.get("notes", f"The task is {mission}")
    return {"notes": llm.invoke(f""" You are tasked with taking notes of everything we learned about this linux system in a structured way.
                                Keep your notes containing only hard facts in markdown and prune them regularly to only keep relevant facts.
                                Try to stay within 25 Lines only write about things we know not about the task.
                                Here are your current notes:
                                {notes} 
                                Here is a tool we called {tool_call} 
                                which gave us this output {tool_response}""").content}
```

This function performs the following actions:

- **Extracting Information:** Retrieves the mission statement (first prompt made), the last tool call, and the output that the tool call returned.
- **Generating Notes:** Utilizes the LLM to format and update the notes, ensuring they remain concise and relevant.
- **Returning Updated State:** Outputs the updated notes to be stored in the shared state.

Let's break down the scribe prompt:

```python
f"""You are tasked with taking notes of everything we learned about this linux system in a structured way.
Keep your notes containing only hard facts in markdown and prune them regularly to only keep relevant facts.
Try to stay within 25 Lines only write about things we know not about the task.
Here are your current notes:
{notes} 
Here is a tool we called {tool_call} 
which gave us this output {tool_response}"""
```

This prompt is used to generate the notes. Telling it to stick with markdown and prune the notes to only keep relevant facts will keep the notes from getting too long and cluttered. It will also come in handy later when we present the notes to the user.

#### 3. **Wiring the Scribe into the Workflow**

To ensure the Scribe operates seamlessly within our graph, we need to integrate it as a node in the state graph. 
There are multiple ways to go about this but we decided to add the Scribe node as a node in the graph right after the tools node.

And within the graph builder:

```python
graph_builder.add_node("scribe", scribe)
graph_builder.add_edge("tools", "scribe")
graph_builder.add_edge("scribe", "chatbot")
```

This setup ensures that after a tool is executed, the Scribe processes the outcome before returning control to the executor.

#### 4. **Testing the Scribe Integration**

After implementing the Scribe node, it's essential to validate its functionality. Run the agent and monitor the notes panel to ensure that notes are being captured and updated correctly. Here's a snippet from the main execution flow:

```python
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
```

This block ensures that the notes are displayed in real-time, providing a clear overview of the information being captured.

Here is a video of the Scribe in action, you can reproduce it by running `python src/executor_and_scribe.py`:
<video src="/screencast_offensive_graph.mp4" controls></video>


#### 5. **Managing Shared State with the Scribe**
Let's move from our small example to a more complex one by integrating the Scribe into the `plan_and_execute` graph:
Our shared state (`PlanExecute`) must accommodate the notes taken by the Scribe. Here's the updated structure:

```python
class PlanExecute(TypedDict):
    input: str  # the initial user-given objective
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str  # response from the agent to the user
    notes: str  # structured notes from the Scribe
```

By including the `notes` field, all nodes within the graph can access and update the notes as required.

#### 6. **Enhancing the Replanner with Scribe Notes**

The Replanner leverages the notes to refine future plans. Here's an excerpt showcasing this integration:

```python
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

Your notes are:
{notes}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.

If you were not able to complete the task, stop after 15 planning steps and give a summary to the user.
"""
)
```

Notice the inclusion of `{notes}` in the prompt, allowing the Replanner to make informed decisions based on the accumulated notes.

### Conclusion

The addition of the Scribe node has been transformative for our plan-and-execute architecture. By meticulously capturing and managing contextual information, we've not only optimized the performance of our LLMs but also enhanced the system's overall reasoning capabilities. This structured approach to note-taking paves the way for more sophisticated and efficient planning mechanisms, setting the stage for future advancements in our multi-agent architecture.

As we continue to refine and expand our system, the Scribe will undoubtedly play a pivotal role in ensuring that our agents remain informed, agile, and capable of tackling increasingly complex tasks with unwavering precision.


