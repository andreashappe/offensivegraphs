import re

from fabric import Connection
from invoke import Responder
from io import StringIO
from langchain_core.tools import tool
from typing import Tuple

GOT_ROOT_REGEXPs = [re.compile("^# $"), re.compile("^bash-[0-9]+.[0-9]# $")]

def got_root(hostname: str, output: str) -> bool:
    for i in GOT_ROOT_REGEXPs:
        if i.fullmatch(output):
            return True

    return output.startswith(f"root@{hostname}:")

class SSHConnection:
    host: str
    hostname: str
    username: str
    password: str
    port: int = 22

    _conn: Connection = None

    def __init__(self, host=None, hostname=None, username=None, password=None, port=22):

        # set default values
        self.host = host
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port

        # create the SSH Connection
        conn = Connection(
            f"{self.username}@{self.host}:{self.port}",
            connect_kwargs={"password": self.password, "look_for_keys": False, "allow_agent": False},
        )
        self._conn = conn
        self._conn.open()
        print("Connected to", str(self._conn))

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        print("conn:" + str(self._conn))
        res = self._conn.run(cmd, *args, **kwargs)
        print("Ran", cmd, "on", str(res))
        return res.stdout, res.stderr, res.return_code
    

# https://python.langchain.com/docs/how_to/custom_tools/#tool-decorator

@tool
def ssh_execute_command(command:str) -> tuple[bool, str]:
        """ Execute command over SSH on the remote machine """

        username = 'lowpriv'
        password = 'trustno1'
        host = '192.168.121.112'
        hostname = 'test-1'
        conn = SSHConnection(host=host, hostname=hostname, username=username, password=password)

        sudo_pass = Responder(
            pattern=r"\[sudo\] password for " + username + ":",
            response=password + "\n",
        )

        out = StringIO()

        print("Executing command:", command)

        try:
            conn.run(command, pty=True, warn=True, out_stream=out, watchers=[sudo_pass], timeout=10)
        except Exception as e:
            print("Expected exception:", e)
            print("TIMEOUT! Could we have become root?")
        out.seek(0)
        tmp = ""
        last_line = ""
        for line in out.readlines():
            if not line.startswith("[sudo] password for " + username + ":"):
                line.replace("\r", "")
                last_line = line
                tmp = tmp + line

        print("cmd executed:", command)
        print("result: ", tmp)

        # remove ansi shell codes
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        last_line = ansi_escape.sub("", last_line)

        return got_root(hostname, last_line), tmp