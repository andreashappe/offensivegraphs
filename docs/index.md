# Welcome to the Playground

## Why are we doing this?

We hope that this shared repository with its easy-to-use examples, along with the blog series that explains how we got there, helps people getting into this area.

- [Andreas](https://github.com/andreashappe) works on using LLMs for offensive security and sees the potential of LLMs to reduce tedious tasks and make security more accessible. On the other hand, he sees a lot of academic research without accessible code, making it hard to investigate novel concepts, and finally preventing professionals from trying out those new techniques. Using LLMs for security is easier than you think.

- [Jürgen](https://github.com/brandl) covers the blue team, forensic analysis side of the team. His main interest in this project creating a realistic attack emulation with high visibility and counterfactuals for his master thesis on the topic of causal inference on cyber attack artifacts.

This is a living project, changing over time. Contributions and collaborators are always welcome.

### Disclaimer

The use of offensivegraphs for attacking targets without prior mutual consent is illegal. It's the end user's responsibility to obey all applicable local, state, and federal laws. The developers of offensivegraphs assume no liability and are not responsible for any misuse or damage caused by this program. Only use it for educational purposes.

## How does this look like?

<video src="/screencast_offensive_graph.mp4" controls></video>

## How is this different to a non-security Project?

Honestly, not much. While we are using specialized tools (functions that LLMs can execute) and are often intentionally malicious prompts, the techniques behind, esp. when it comes to task planing, are the same as with 'normal' use-cases.

We see this as a benefit, we learn using LLMs and offensive security.

## What do we have?

| Example | Domain | Summary | Further Documentation |
| -- | -- | -- | -- |
| [initial example](https://github.com/andreashappe/offensivegraphs/blob/main/src/initial_version.py) | linux priv-esc | good first example | [initial post](blog/posts/2024-10-10-first-steps-and-initial-version.md), [tools and configuration](blog/posts/2024-10-11-configuration-for-tool-calls.md) |
| [react agent](https://github.com/andreashappe/offensivegraphs/blob/main/src/switch-to-react.py) | linux priv-esc | use langgraph to reduce code | [Using `create_react_agent`](blog/posts/2024-10-12-create_react_agent.md) |
| [plan-and-execute](https://github.com/andreashappe/offensivegraphs/blob/main/src/plan_and_execute.py) | linux priv-esc | multi-layer planing | [Adding Plan-and-Execute Planner](blog/posts/2024-10-14-plan-and-exec.md) |

## How did we get there?

We document our journey through blog-posts that explain our prototypes and the decisions behind them:

- [Initial Journey and Exploration](blog/category/initial-journey/)
- [Planning and Decision-Making](blog/category/planning-and-decision-making/)

## How to setup?

```bash
# clone the repository and enter it
$ git clone ...

# cd <repo-name>
$ cd ..

# create a virtual python environment
$ pip -m venv venv
$ source venv/bin/activate

# install dependencies
$ pip install -e .

# setup OPENAI keys, etc.
# First edit env.example, then mv it into .env
$ mv env.example .env

# you're now ready to go!
```

## How to contribute

We try to keep all development open on github at [https://github.com/andreashappe/offensivegraphs] with the exemption that security-critical research might only be released after responsible disclosure with the respective targets.

We're happy to accept contributions [through github pull-requests](https://github.com/andreashappe/offensivegraphs/pulls) as well as bug-reports/ideas at [github's issue tracker](https://github.com/andreashappe/offensivegraphs/issues). Feel free to contact [Andreas](mailto:andreas@offensive.one) in case of questions/ideas.
