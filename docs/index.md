# Welcome to the Playground

## Why are we doing this?

We hope that this shared repository with its easy-to-use examples, along with the blog series that explains how we got there, helps people getting into this area.

- [Andreas](https://github.com/andreashappe) works on using LLMs for offensive security and sees the potential of LLMs to reduce tedious tasks and make security more accessible. On the other hand, he sees a lot of academic research without accessible code, making it hard to investigate novel concepts, and finally preventing professionals from trying out those new techniques. Using LLMs for security is easier than you think.

This is a living project, changing over time. Contributions and collaborators are always welcome.

## How is this different to a non-security Project?

Honestly, not much. While we are using specialized tools (funtions that LLMs can execute) and are often intentionally malicious prompts, the techniques behind, esp. when it comes to task planing, are the same as with 'normal' use-cases.

We see this as a benefit, we learn using LLMs and offensive security.

## What do we have?

| Example | Domain | Summary | Further Documentation |
| -- | -- | -- | -- |
| initial example | linux priv-esc | good first example | blog1, blob2, blog3 |
| react agent | linux priv-esc | use langgraph to reduce code | blog |
| plan-and-execute | linux priv-esc | multi-layer planing | blog |

## How did we get there?

We document our journey through blog-posts that explain our prototypes and the decisions behind them:

- [Initial Journey and Exploration](/blog/category/initial-journey/)
- [The Road to Windows]()

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

- link to github and github issues