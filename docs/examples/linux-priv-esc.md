# Linux Privilege Escalation

These examples try to solve the following scenario:

- the attacker has low-level (non-`root`) access to a virtual machine through SSH.
- they know their username and the respective password
- and want to become the all powerful root user (`uid=0`)

## Example Implementations

These examples are currently available through our github repository:

| Example | Domain | Summary | Described in|
| -- | -- | -- | -- |
| [initial example](https://github.com/andreashappe/offensivegraphs/blob/main/src/initial_version.py) | linux priv-esc | good first example | [initial post](../blog/posts/2024-10-10-first-steps-and-initial-version.md), [tools and configuration](../blog/posts/2024-10-11-configuration-for-tool-calls.md) |
| [react agent](https://github.com/andreashappe/offensivegraphs/blob/main/src/switch-to-react.py) | linux priv-esc | use langgraph to reduce code | [Using `create_react_agent`](../blog/posts/2024-10-12-create_react_agent.md) |
| [plan-and-execute](https://github.com/andreashappe/offensivegraphs/blob/main/src/plan_and_execute.py) | linux priv-esc | multi-layer planing | [Adding Plan-and-Execute Planner](../blog/posts/2024-10-14-plan-and-exec.md) |