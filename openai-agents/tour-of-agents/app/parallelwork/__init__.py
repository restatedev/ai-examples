"""Parallel work agents module."""
from .parallel_agents import parallel_agent_claim_approval
from .parallel_tools_agent import parallel_tool_claim_agent

__all__ = ["parallel_agent_claim_approval", "parallel_tool_claim_agent"]