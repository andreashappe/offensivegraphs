import os

from dataclasses import dataclass
from fabric import Connection
from invoke import Responder
from io import StringIO
import paramiko
from pydantic import BaseModel, Field
from typing import Tuple, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool

@dataclass
class SSHConnection:
    host: str
    hostname: str
    username: str
    password: str
    port: int = 22

    _conn: Connection = None

    def connect(self):
        # create the SSH Connection
        conn = Connection(
            f"{self.username}@{self.host}:{self.port}",
            connect_kwargs={"password": self.password, "look_for_keys": False, "allow_agent": False},
        )
        self._conn = conn
        self._conn.open()

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        if self._conn is None:
            raise Exception("SSH Connection not established")
        res = self._conn.run(cmd, *args, **kwargs)
        return res.stdout, res.stderr, res.return_code
    
    def new_SSHConnection_with(self, *, host=None, hostname=None, username=None, password=None, port=None) -> "SSHConnection":
        return SSHConnection(
            host=host or self.host,
            hostname=hostname or self.hostname,
            username=username or self.username,
            password=password or self.password,
            port=port or self.port,
        )

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

    def __init__(self, conn: SSHConnection):
        super(SshExecuteTool, self).__init__(conn=conn)

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

class SshTestCredentialsInput(BaseModel):
    username: str= Field(description="the username to test")
    password: str= Field(description="the password to test")

# Note: It's important that every field has type hints. BaseTool is a
# Pydantic class and not having type hints can lead to unexpected behavior.
class SshTestCredentialsTool(BaseTool):
    name: str = "SshTestCredentialsTool"
    description: str = "Test if username/password credentials are valid on the remote system."
    args_schema: Type[BaseModel] = SshTestCredentialsInput
    return_direct: bool = True
    conn: SSHConnection

    def __init__(self, conn: SSHConnection):
        super(SshTestCredentialsTool, self).__init__(conn=conn)

    def _run(self, username:str, password:str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        test_conn = self.conn.new_SSHConnection_with(username=username, password=password)
        try:
            test_conn.connect()
            user = test_conn.run("whoami")[0].strip("\n\r ")
            if user == "root":
                return "Login as root was successful\n"
            else:
                return "Authentication successful, but user is not root\n"

        except paramiko.ssh_exception.AuthenticationException:
            return "Authentication error, credentials are wrong\n"
        
def get_or_fail(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Environment variable {name} not set")
    return value

def get_ssh_connection_from_env() -> SSHConnection:
    host = get_or_fail("TARGET_HOST")
    hostname = get_or_fail("TARGET_HOSTNAME")
    username = get_or_fail("TARGET_USERNAME")
    password = get_or_fail("TARGET_PASSWORD")

    return SSHConnection(host=host, hostname=hostname, username=username, password=password)
