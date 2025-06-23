# AWS Labs rds-management MCP Server

An AWS Labs Model Context Protocol (MCP) server for rds-management

## Instructions

Instructions for using this rds-management MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/rds_management_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this rds-management MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/rds-management-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: rds-management MCP Server
    ---

    {% include "../../src/rds-management-mcp-server/README.md" %}
    ```
  
* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### rds-management MCP Server
    
    An AWS Labs Model Context Protocol (MCP) server for rds-management
    
    **Features:**
    
    - Feature one
    - Feature two
    - ...

    Instructions for using this rds-management MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.
    
    [Learn more about the rds-management MCP Server](servers/rds-management-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
