---
authors:
    - andreashappe
date: 2024-10-11
categories:
    - 'initial journey'
---
# Tool Calls and Configuration

- https://api.python.langchain.com/en/latest/core/tools/langchain_core.tools.base.BaseTool.html
- https://python.langchain.com/docs/how_to/custom_tools/
- https://api.python.langchain.com/en/latest/tools/langchain_core.tools.tool.html

## want to fix:

- maybe switch tool to tool-base class
- config handling could be cleaner
- ToolMessages are only shown for a single tool, not sure why

## Notes

done in `26c02488e7da504cade55fda0094225bac055f01`

warning: initially, I got `return_direct` wrong leading to the following fix `576105f2a358c7aa6877d3bcf0395a5ec2997e7f`