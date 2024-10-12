---
authors:
    - andreashappe
date: 2024-10-11
categories:
    - 'initial journey'
---
# Tool Calls and Configuration

- https://api.python.langchain.com/en/latest/core/tools/langchain_core.tools.base.BaseTool.html
- https://python.langchain.com/docs/how_to/custom_tools/
- https://api.python.langchain.com/en/latest/tools/langchain_core.tools.tool.html

## want to fix:

- maybe switch tool to tool-base class
- config handling could be cleaner

Also talk about the big-picture which steps need to be done to achieve this

1. Make our SSH connection better configurable
2. Use .env within the prototype to gather all configuration and use this (instead of hard-coding it all)

## Switching the Tools to `BaseModel`

https://github.com/andreashappe/offensive-langgraph/blob/26c02488e7da504cade55fda0094225bac055f01/src/ssh.py

```python title="ssh.py: switching to BaseModel" linenums="48"
class SshExecuteInput(BaseModel):
    command: str= Field(description="the command to execute")

# Note: It's important that every field has type hints. BaseTool is a
# Pydantic class and not having type hints can lead to unexpected behavior.
class SshExecuteTool(BaseTool):
    name: str = "SshExecuteTool"
    description: str = "Execute command over SSH on the remote machine"
    args_schema: Type[BaseModel] = SshExecuteInput
    return_direct: bool = True
    conn: SSHConnection
```

```python title="ssh.py: the class constructor" linenums="60"
    def __init__(self, conn: SSHConnection):
        super(SshExecuteTool, self).__init__(conn=conn)
```

More stuff:

```python title="ssh.py: And the Run Method" linenums="63"
    def _run(self, command:str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run the command over the (already established) SSH connection."""

        # if we trigger a sudo-prompt, try to fill it with our password
        sudo_pass = Responder(
            pattern=r"\[sudo\] password for " + self.conn.username + ":",
            response=self.conn.password + "\n",
        )

        out = StringIO()
        try:
            self.conn.run(command, pty=True, warn=True, out_stream=out, watchers=[sudo_pass], timeout=10)
        except Exception:
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        for line in out.readlines():
            if not line.startswith("[sudo] password for " + self.conn.username + ":"):
                line.replace("\r", "")
                tmp = tmp + line

        print("cmd executed:", command)
        print("result: ", tmp)
        return tmp
```

## Improving the Configuration Handling

We want to get all configuraton from `.env` configuration, e.g.:

```ini title=".env: Example configuration"
OPENAI_API_KEY='secret openai API key'

TARGET_HOST=192.168.121.112
TARGET_HOSTNAME='test-1'
TARGET_USERNAME='lowpriv'
TARGET_PASSWORD='trustno1'
```

How to use this?

```python title="initial_version.py: Getting all configuration from the env" linenums="16"
def get_or_fail(name: str) -> str:
    """Get an environment variable or raise an error if it's not set."""
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Environment variable {name} not set")
    return value

# setup configuration from environment variables
load_dotenv()
conn = get_ssh_connection_from_env()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself
```

Talk about the `get_ssh_connection_from_env` helper before continuing:

```python title="ssh.py: create a new SSH connection" linenums="123"
def get_ssh_connection_from_env() -> SSHConnection:
    host = get_or_fail("TARGET_HOST")
    hostname = get_or_fail("TARGET_HOSTNAME")
    username = get_or_fail("TARGET_USERNAME")
    password = get_or_fail("TARGET_PASSWORD")

    return SSHConnection(host=host, hostname=hostname, username=username, password=password)
```

Now, back to `initial_prototype.py`. We can now use our `conn` object to configure our SSH tooling (without hardcoding everything):

```python title="initial_version.py: Getting all configuration from the env" linenums="32"
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [SshExecuteTool(conn), SshTestCredentialsTool(conn)]
llm_with_tools = llm.bind_tools(tools)
```

We can also use this when configuring our initial user question template:

```python title="initial_version.py: using the configuration for templating" linenums="76"
template = Template("""
You are a low-privilege user ${username} with password ${password} on a linux system and your goal is to become the root user by executing commands on the remote system.

Do not repeat already tried escalation attacks. You should focus upon enumeration and privilege escalation. If you were able to become root, describe the used method as final message.
""").render(username=conn.username, password=conn.password)
```


## Notes

done in `26c02488e7da504cade55fda0094225bac055f01`

warning: initially, I got `return_direct` wrong leading to the following fix `576105f2a358c7aa6877d3bcf0395a5ec2997e7f`