async def request_mcp_approval(mcp_tool_name: str, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {mcp_tool_name}")
    print(f"  Submit your mcp tool approval via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json true"
    )
