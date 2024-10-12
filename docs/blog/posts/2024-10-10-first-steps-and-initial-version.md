---
authors:
    - andreashappe
date: 2024-10-10
categories:
    - 'initial journey'
---
# First Steps and Initial Version

This started when [Juergen]() contacted [Andreas]() as he needed an automated attacker emulation for one of his defensive projects. Andreas wrote the initial version of [hackingBuddyGPT](https://hackingbuddy.ai) in March 2023 (roughly 18 months ago) and much of the codebase was written for older, less-sophisticated, LLMs. Juergen had experience with [LangGraph](https://www.langchain.com/langgraph), so we decided to play around with using langgraph for offensive security.

## Scencario and Starting Situation

As an initial example we have chosen Linux Privilege Escalation: in these scenarios, you already have access to a linux system (typically over SSH) as a low-privilege user and want to become the all powerful root user.

As a starting point, we were using both [langgaph's quickstart tutorial](https://langchain-ai.github.io/langgraph/tutorials/introduction/) for rough guidance, as well as Andreas' original SSH connector to connect to a vulnerable virtual machine provided by [ipa-lab/benchmark-privesc-linux](https://github.com/ipa-lab/benchmark-privesc-linux) (also originally written by Andreas).

The following langgraph pages give good background knowledge:

- [The Langgraph starting page](https://langchain-ai.github.io/langgraph/)
- [Langraph QuickStart](https://langchain-ai.github.io/langgraph/tutorials/introduction/) (part of the tutorial series)
- More information about `tool usage` can also be found [within the documentation](https://python.langchain.com/docs/how_to/custom_tools/#tool-decorator)

## The First Prototype

This prototype source code can be found [in the github history](https://github.com/andreashappe/offensive-langraph/tree/64ae8a080c5aa5e7255e1cb00c8ddb5adc6d1a20). If you look into the current `main` branch, the current source code will look differently.

We split the functionality into two files: `ssh.py` for all the SSH callouts performed by the prototype, and `initial_version.py` containg the actual prototype logic.

### Tool-Calling: enable SSH command execution

Tools allow LLMs to access external operations. In our case, we want LLMs to execute commands over SSH on a remote host. Let's go through parts of the code in `ssh.py`:

```python title="ssh.py: Declare the Tool Function" linenums="33"
@tool
def ssh_execute_command(command:str) -> str:
        """ Execute command over SSH on the remote machine """
```

We initially started by using [langchain's @tool annotation](https://langchain-ai.github.io/langgraph/how-tos/pass-run-time-values-to-tools/#define-the-tools) (line 33). This will later allow LLMs to call the `ssh_execute_command` function. It is important to give a good docstring, as this will be automatically be used to explain the purpose of the tool to the LLM. Parameters and output values will automagically be matched too!

```python title="ssh.py: Open the SSH connection" linenums="37"
        username = 'lowpriv'
        password = 'trustno1'
        host = '192.168.121.112'
        hostname = 'test-1'
        conn = SSHConnection(host=host, hostname=hostname, username=username, password=password)
        conn.connect()
```

This is ugly hard-coded cruft. We open a SSH connection to a hard-coded target host. We will make this configurable in the next blog post.

```python title="ssh.py: Execute a command and return a value" linenums="44"
        sudo_pass = Responder(
            pattern=r"\[sudo\] password for " + username + ":",
            response=password + "\n",
        )

        out = StringIO()
        try:
            conn.run(command, pty=True, warn=True, out_stream=out, watchers=[sudo_pass], timeout=10)
        except Exception:
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        for line in out.readlines():
            if not line.startswith("[sudo] password for " + username + ":"):
                line.replace("\r", "")
                tmp = tmp + line

        print("cmd executed:", command)
        print("result: ", tmp)
        return tmp
```

This is the actual code that executes a SSH command and captures it's output. This is also old cruft and hopefully looks better in the current version within the repository.

The import thing to note is line 63: here we return the output of the executed command as string from the fuction. LangChain will take this output and return it to the LLM as result of the tool call.

### The Privilege Escalation Prototype

Let's go the 'meat' of the code, the langgraph agent in `initial_version.py`:

```python title="initial_version.py: Setup" linenums="16"
# Load environment variables
load_dotenv()

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")
```

Lots of stuff going on here in the background. We're using [python-dotenv](https://pypi.org/project/python-dotenv/) through calling `load_dotenv`. This looks for a `.env` file in the curent working directory and load environmental variables from it (if they are not already configured within the environment). Variables like these are typically used to pass API-keys and similar to programs.

The one environmental variable in use is `OPENAI_API_KEY` which is used to connect to OpenAI. Lines 19-23 were copied from the quickstart. They check if the environable variable is set and ask the user for it otherwise. This variable itself will be used by langchain and langgraph itself, so we do not have to do anything with it explicitely.

```python title="initial_version.py: Connect to the LLM and setup Tools" linenums="26"
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [ssh_execute_command]
llm_with_tools = llm.bind_tools(tools)
```

Now we create a connection to the LLM (`gpt-4o` in our case) and register some tools that the LLM is allowed to use. As tool, we are using the `ssh_execute_command` function we described before.


```python title="initial_version.py: Begin with our Graph" linenums="31"
class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)
```

Now it gets interessting: we start with defining our langgraph graph. Within langgraph, you are using `Nodes` and `Edges`. The nodes in your graph are the "action points". Those are the locations, where you perform operations or ask a LLM to decide or perform stuff for you. Within the python code, each node will be implemented as a python function (see below). Edges define, which nodes are allowed to pass on information to other nodes.

The information passed between nodes is stored in the `State`. In our case, we just use a list of `messages`. `Annotated` is from python's `typing` library and allows us to add some metadata to the `messages` variable. In this case, we store the method `add_messages` as meta-data. Langgraph will know through this, that if new messages are added, it will call `add_messages` to add the messages to the list. In our case, we just have a growing list, but you could implement a sliding window or some sort of compaction/compression mechnism through this.

Finally, we create our graph (named `graph_builder`). We tell it that `State` will be used to pass messages.


```python title="initial_version.py: Our first node, the LLM call" linenums="38"
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}
```

Within those two lines, a lot happens! We define our first graph node (called `chatbot` as this was copied out of the tutorial). What is it doing? It takes all messages that are stored within the state (`state["messages"]`) and calls out to the LLM. As the first message in the list (as you will see below) is the task that the LLM should achieve, this will give the LLM the task as well as a history about all other actions that already have been taken.

The output of the LLM (typically a `str`) will be put into an array (and in turn put into a map), thus the output of the node will be, e.g., `{ "messages" : [ "the LLM output" ]}`. As configured above, the `add_messages` method will be used to append this to `state['messages']`.

```python title="initial_version.py: Let's build our graph" linenums="56"
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", route_tools)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("chatbot", END)
```

Let's start with finally creating our graph. We add our LLM-calling node (`chatbot`) and then add a predefined `ToolNode`. This is a node that will receive messages about calling tools, e.g., allowing the LLM to interact with the world. To let it know which tools are supported, we pass the same `tools` into it as we registered with the LLM (makes sense, both should know the same tool calls or would get out-of-sync).

Then we start to create the edges between our nodes. There are special `START` and `END` nodes that denote the graphs starting and ending points (d'oh, lines 59 and 62). We connect the chatbot to the tool node on line 60, and connect back the tool node to the chatbot on line 61. So the LLM bot might create a message for the user (the result to the incoming question) or might create a tool-call message. The Tool node would take the tool-call message and interact with the external world and then pass back the result to the LLM node.

This creates an infinite loop and we cannot have that, can we? This is why on line 60 we define a condition edge: this is an edge with a condition that can dynamically select the next action (node) to perform. To do this, we define the `route_tools` method:

```python title="initial_version.py: either call a tool, or quit" linenums="41"
def route_tools(state: State):
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END
```

This was copied verbose from the tutorial. In summary, it checks if there's a message within the state. If it has a message and the message is a `tool_calls` message, i.e., we want to execute an external tool, the next node/action will be our tool node. Otherwise we go to the `END` node and finish our graph. Why does this work? Well, as long as there are tool calls, the tools will be executed and the results appended to the end of the message log. As soon as the LLM can find an answer, it will send out the answer (not a `tool_call`), thus the `route_tools` method will go to the `END` node.


```python title="initial_version.py: finalize the graph!" linenums="66"
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)
```

Now we create the graph. What is `MemorySaver`? This stores our state between interactions (gives us a in-memory storage while running our agent).

Now, what to use as our initial message (this will be the first message within our `state['messages'] list and task our LLM to "do stuff"). We're using an adapted prompt from our hackingBuddyGPT prototype:


```python title="initial_version.py: The initial user question for the LLM" linenums="70"
template = Template("""
You are a low-privilege user ${username} with password ${password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").render(username="lowpriv", password="trustno1")
```

As this was taken from my old code, it still uses the `Mako` template engine (could be replaced with a f-String or similar by now). Also, note that we hard-coded the same credentials as within the `SSHConnection` before, we will fix this in the next blog-post.

The prompt itself is quite simple, isn't it?

```python title="initial_version.py: Start and output it" linenums="76"
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
for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()
```

Now, the final step: through `graph.stream` we start the graph and give it the initial task (the just mentioned question from `template`). Using `stream_mode="values"` (line 85) will create an event stream will the messages that are passing through the graph.

We use this events on line 88 to watch for potential changes. This allows us to output everything that is happening during exeuction.

### The graph in it's full glory

TODO add graph

## Execute it!

TODO

## Next Steps and TODOs

There are some things that need to be cleaned up.

switch from the `@tool`-annotation to the `BaseModel` base-class to allow tool configuration. We want to setup the SSH-connection (hostname, username, password) in the beginning and not hard-code it within our code. This will also clean-up our configuration handling.

The `langchain` library itself offers simple templating ([PromptTemplate](https://api.python.langchain.com/en/latest/prompts/langchain_core.prompts.prompt.PromptTemplate.html)) thus making using a seperate `mako` template engine superficious. Sometime after I wrote this documention, I replaced the mako template with:

```python
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)
```
