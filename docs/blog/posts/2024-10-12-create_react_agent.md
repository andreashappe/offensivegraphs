---
authors:
    - andreashappe
date: 2024-10-12
categories:
    - 'initial journey'
---
# Simplify our Tool-Calling Agent through `create_react_agent`

LangGraph has some amazing [Prebuilt Components](https://langchain-ai.github.io/langgraph/reference/prebuilt/), one of them is the [`create_react_agent` function](https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.chat_agent_executor.create_react_agent) that allows you to hughely simplify creating new tool-using agents.

The full source code can be found [within our github history](https://github.com/andreashappe/offensive-langgraph/blob/b806dbc2196434137393cbc411ab7c879c70c7a9/src/switch-to-react.py).

## The simplified version

This willb e based upon our [recent configuration-improved version](). Similar to that version, we start by reading the configuration data, setting up our LLM, connecting to the target system via SSH, and configuring tools for usage through LLMs:

```python title="Initial Configuration" linenums="10"
# setup configuration from environment variables
load_dotenv()
conn = get_ssh_connection_from_env()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself

# connect to the target system over SSH
conn.connect()

# initialize the ChatOpenAI model and register the tool (ssh connection)
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [SshExecuteTool(conn), SshTestCredentialsTool(conn)]
```

Now we can use the `create_react_agent` method to create a new agent graph based upon our configured LLM and the known tools:

```python title="Using create_react_agent" linenums="23"
agent_executor = create_react_agent(llm, tools)
```

All that's left is to create the initial message (as detailed in our [initial blog post]()) and start the agent by calling `stream` on it while passing the mentioned initial message.

Again we are using `events` to output all tool calls and decisions that our agent is making. 

```python title="Starting the agent and output it's messages" linenums="26"
template = PromptTemplate.from_template("""
You are a low-privilege user {username} with password {password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").format(username=conn.username, password=conn.password)


events = agent_executor.stream(
    {
        "messages": [
            ("user", template),
        ]
    },
    stream_mode="values",
)

for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()
```

And that's it! Pretty amazing, when you think about it.

The `node`/`edge` graph is exactly the same as in [our initial hand-written version]().