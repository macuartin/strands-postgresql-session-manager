"""
PostgreSQL Session Manager for Strands Agents SDK.

A high-performance session manager that uses PostgreSQL for persistent storage
of agent conversations and state with full ACID guarantees.

Example:
    >>> from sqlmodel import create_engine
    >>> from strands import Agent
    >>> from strands_postgresql_session_manager import PostgresSessionManager
    >>>
    >>> # Create PostgreSQL engine
    >>> engine = create_engine("postgresql://user:pass@localhost:5432/agents")
    >>>
    >>> # Create session manager
    >>> session_manager = PostgresSessionManager(
    ...     session_id="user_123",
    ...     engine=engine
    ... )
    >>>
    >>> # Use with Strands Agent
    >>> agent = Agent(session_manager=session_manager)
    >>> agent("Hello! Tell me about PostgreSQL.")
"""

from .session_manager import PostgresSessionManager
from .models import SessionDB, AgentDB, MessageDB

__version__ = "0.1.0"
__all__ = [
    "PostgresSessionManager",
    "SessionDB",
    "AgentDB",
    "MessageDB",
]
