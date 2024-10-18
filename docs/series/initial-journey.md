# Security Agents with LangGraph

This is our initial foray into using LangChain/LangGraph for security agents. The blog series should be usable as an introduction for new developers that want to do something similiar.

## Basic Concepts

| Date | Blog Post | Description |
| --- | --- | --- |
| 10.10.2024 | [First Steps and Initial Version](./../blog/posts/2024-10-10-first-steps-and-initial-version.md) | Creating a first autonomous linux priv-esc agent using langgraph. Introduce `ssh connection` as Tool so that the agent can execute commands over SSH. |
| 11.10.2024 | [Improving Configuration Handling, esp. for Tools](./../blog/posts/2024-10-11-configuration-for-tool-calls.md) | Remove Hardcoded Configuration and improve Tool-Integration. |
| 12.10.2024 | [Simplify our Tool-Calling Agent through `create_react_agent`](./../blog/posts/2024-10-12-create_react_agent.md) | LangGraph offers a prebuilt react agent that highly simplifies our code (albeit does not allow us to further customize the agent flows). |
