---
authors:
    - andreashappe
date: 2024-10-11
categories:
    - 'initial journey'
---
# Improving Configuration Handling, esp. for Tools

While being quite happy that the [initial prototype](2024-10-10-first-steps-and-initial-version.md) worked within hours, its code was very prototype-y, i.e., much of its configuration was hard-coded. In a second step, we want to fix this by making our target information (the SSH connection) configurable and remove all hard-coded credentials from the code.

## Big Picture

We are already using [python-dotenv](https://pypi.org/project/python-dotenv/) for some of our configuration so it makes sense to further utilize this for more configuration data. In the improved implementation, our `.env` will look like this:

```ini title=".env: Example configuration"
OPENAI_API_KEY='secret openai API key'

TARGET_HOST=192.168.121.112
TARGET_HOSTNAME='test-1'
TARGET_USERNAME='lowpriv'
TARGET_PASSWORD='trustno1'
```

The prototype will read this for configuration data. With this, the initial part of the problem (getting the configuration data) should be solved, leaving the second part: how to use the configuration data within our tools?

After looking into the [@tool annotation](https://api.python.langchain.com/en/latest/tools/langchain_core.tools.tool.html) for functions, this did not look like the perfect approach. Instead we opted towards subclassing [BaseTool](https://api.python.langchain.com/en/latest/core/tools/langchain_core.tools.base.BaseTool.html). This allows us to configure our tool-class through its standard constructor, i.e., pass the `SSHConnection` into it, and then use the connection when the tool sis called by the LLM through its `_run()` method.

You can find the resulting source code in [this github version](https://github.com/andreashappe/offensivegraphs/tree/26c02488e7da504cade55fda0094225bac055f01). Please note, that I had a bug initially ([fixed here](https://github.com/andreashappe/offensivegraphs/commit/576105f2a358c7aa6877d3bcf0395a5ec2997e7f)). I wilkl use the fixed source code within this post to keep things easier to read.

Let's start with our updated tool that will be configurable:

## Making our Tool configurable by switching to `BaseTool`

You can find the full source code at [within github](https://github.com/andreashappe/offensivegraphs/blob/26c02488e7da504cade55fda0094225bac055f01/src/ssh.py). This change was pretty straight-forward.

Instead of writing a function, we now create a class for each tool. We have to subclass [BaseTool](https://api.python.langchain.com/en/latest/tools/langchain_core.tools.BaseTool.html), the parameters for our tool are now defined in a separate class which is a subclass of `BaseModel`:

```python title="ssh.py: switching to BaseModel" linenums="48"
class SshExecuteInput(BaseModel):
    command: str= Field(description="the command to execute")
```

Now for the tool class:

```python title="ssh.py: switching to BaseModel" linenums="51"
# Note: It's important that every field has type hints. BaseTool is a
# Pydantic class and not having type hints can lead to unexpected behavior.
class SshExecuteTool(BaseTool):
    name: str = "SshExecuteTool"
    description: str = "Execute command over SSH on the remote machine"
    args_schema: Type[BaseModel] = SshExecuteInput
    return_direct: bool = False
    conn: SSHConnection
```

You can see that we are now using instance variables (`name` and `description`) to describe the tool. `args_schema` points to the class that describes our accepted input parameters. `return_direct` is set to `False`. If set to `True`, langgraph agents will stop when the Tool stops. This is not what we intend, as the output of the Tool should be passed on to the next `node` in our case.

Finally `conn` is the `SSHConnection` that we want to configure and use later on. Next, we set it through the class constructor:

```python title="ssh.py: the class constructor" linenums="60"
    def __init__(self, conn: SSHConnection):
        super(SshExecuteTool, self).__init__(conn=conn)
```

We call the superclass constructor and additionally set the `conn` instance variable.

Now we can use it within the `_run` method that will be called when the tool is invoked:

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

Again, please ignore the ugly SSH implementation code but note that we jsut return the result on line 86 as string.

Next step is wiring everything up within our prototype code.

## Improving the Configuration Handling

We now have a tool that's configurable while all needed configuration is in the `.env` file. Let's connect them! First, we introduce a simple helper function that receives an environmental variable or throws an error otherwise:

```python title="initial_version.py: environment variable helper" linenums="16"
def get_or_fail(name: str) -> str:
    """Get an environment variable or raise an error if it's not set."""
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Environment variable {name} not set")
    return value
```

Now we can use `load_dotenv()` to load the variables set within `.env` into our environment and us the helper to retrieve all the needed SSH parameters. With this data we can finally create our `SSHConnection`. We extracted this into a separate method for readability:

```python title="ssh.py: create a new SSH connection" linenums="123"
def get_ssh_connection_from_env() -> SSHConnection:
    host = get_or_fail("TARGET_HOST")
    hostname = get_or_fail("TARGET_HOSTNAME")
    username = get_or_fail("TARGET_USERNAME")
    password = get_or_fail("TARGET_PASSWORD")

    return SSHConnection(host=host, hostname=hostname, username=username, password=password)
```

Finally, we can wire everything up within our [prototype](https://github.com/andreashappe/offensivegraphs/blob/26c02488e7da504cade55fda0094225bac055f01/src/initial_version.py):

```python title="initial_version.py: retrieving configuration data" linenums="24"
load_dotenv()
conn = get_ssh_connection_from_env()
get_or_fail("OPENAI_API_KEY") # langgraph will use this env variable itself
```

Note that we now have a configured SSH connection within `conn`. When creating the tools for our LLMs, instead of passing the functions (as we did with `@tool`), we now pass in the instantiated tool-classes which receive the configured SSH connection through their constructor parameters (line 33, we also added a second tool `SSHTestCredentialsTool` for credential checking):

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

And that's it.
