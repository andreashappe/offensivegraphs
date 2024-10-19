from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

@dataclass
class Task:
    timestamp: str
    step: int
    payload_id: str
    name: str
    input: str
    result: str = ''

class RichLogger:

    events = []
    console = None
    open_tasks = {}
    finished_tasks = []

    def __init__(self):
        self.console = Console()
        # todo: create log file path

    def process_single_message(self, message):
        if isinstance(message, ToolMessage):
            self.console.print(Panel(message.content, title=f"{message.name} answers"))
        elif isinstance(message, AIMessage):
            for call in message.tool_calls:
                self.console.print(Panel(Pretty(call['args']), title=f"Outgoing Tool to {call['name']}"))
        elif isinstance(message, HumanMessage):
            self.console.print(Panel(message.content, title="Initial (Human?) Query"))
        else:
            self.console.print(Panel(Pretty(message), title="Unknown Message Type!"))

    def process_messages(self, messages):
        for message in messages:
            self.process_single_message(message)

    def process_debug_event(self, event):
        if event['type'] == 'task':
            task = Task(event['timestamp'], event['step'], event['payload']['id'], event['payload']['name'], event['payload']['input'])
            self.open_tasks[task.payload_id] = task
            self.console.log(f"{task.timestamp}/{task.step}: started {task.name}")
            if 'messages' in event['payload']['input']:
                self.console.log("messages found, last one:")
                self.print_message(event['payload']['input']['messages'][-1])
            else:
                self.console.log(task.input)
        elif event['type'] == 'task_result':
            task = self.open_tasks[event['payload']['id']]
            assert(task.step == event['step'])
            assert(task.name == event['payload']['name'])
            task.result = event['payload']['result']
            del self.open_tasks[task.payload_id]
            self.finished_tasks.append(task)
            self.console.log(f"finshed task {task.name}")
            if task.name == 'tools':
                for (type, messages) in event['payload']['result']:
                    in_there = False
                    for message in messages:
                        in_there = True
                        self.process_single_message(message)
                    if not in_there:
                        self.console.log(Pretty(messages))
            elif 'messages' in event['payload']['result']:
                self.console.log("messages found, last one:")
                self.print_message(event['payload']['result']['messages'][-1])
            else:
                in_there = False
                for (type, messages) in event['payload']['result']:
                    if type == 'plan':
                        in_there = True
                        self.process_single_message(messages)
                    else:
                        for message in messages:
                            in_there = True
                            self.process_single_message(message)
                if not in_there:
                   self.console.log(task.result)
        else:
            self.console.print(Pretty(event))

    def capture_event(self, event):
        self.events.append(event)
        # todo: write data to logfile for long-term tracing

        if 'type' in event:
            self.process_debug_event(event)
        elif 'messages' in event:
            self.process_messages(event['messages'])
        else:
            self.console.print(Panel(Pretty(event), title="Unknown Event Type!"))

    def print_message(self, message):
        if isinstance(message, AIMessage):
            if len(message.tool_calls) > 0 and len(message.content) == 0:
                for tool_call in message.tool_calls:
                    self.console.print(Panel(Pretty(tool_call['args']), title=f"Tool call to {tool_call['name']}"))
            else:
                self.console.log(Pretty(message))
        elif isinstance(message, HumanMessage):
            self.console.print(Panel(message.content, title="Initial Message"))
        elif isinstance(message, ToolMessage):
            self.console.print(Panel(message.content, title="Answer from Tool"))
        else:
            self.console.log(Pretty(message))