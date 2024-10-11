---
authors:
    - andreashappe
date: 2024-10-10
categories:
    - 'initial journey'
---
# Initial Version

Good starting background documentation:

- https://langchain-ai.github.io/langgraph/
- https://langchain-ai.github.io/langgraph/tutorials/introduction/
- https://python.langchain.com/docs/how_to/custom_tools/#tool-decorator

# project setup for beginners

- git clone (with commit)
- how to install dependencies
- how to setup .env

# our starting situation

- having some SSH code from hackingbuddyGPT
- code from the different langchain-examples

# the first prototype

- move SSH code into separate SSH file
- implement a simple manually-written version
- remove much of the old cargocult-ish fixes that might not be needed anymore (with modern LLMs)

# TODO

- maybe switch tool to tool-base class
- config handling could be cleaner
- ToolMessages are only shown for a single tool, not sure why

## Other todos

- can we replace the Make template engine with something else?
- also output the graph
