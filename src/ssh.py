from dataclasses import dataclass
from fabric import Connection
from invoke import Responder
from io import StringIO
from langchain_core.tools import tool
from typing import Tuple

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

@tool
def ssh_execute_command(command:str) -> str:
        """ Execute command over SSH on the remote machine """

        username = 'lowpriv'
        password = 'trustno1'
        host = '192.168.121.112'
        hostname = 'test-1'
        conn = SSHConnection(host=host, hostname=hostname, username=username, password=password)
        conn.connect()

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