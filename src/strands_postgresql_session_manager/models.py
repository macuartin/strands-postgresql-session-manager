"""
SQLModel database models for PostgreSQL session storage.

These models define the database schema for storing Strands Agent
sessions, agents, and messages with full ACID guarantees.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, ForeignKey


class SessionDB(SQLModel, table=True):
    """
    Session database model for Strands Agents.

    Maps to the 'sessions' table in PostgreSQL.
    Stores conversation sessions with metadata.

    Attributes:
        session_id: Unique identifier for the session (PRIMARY KEY)
        session_type: Type of session (e.g., 'AGENT', 'MULTI_AGENT')
        created_at: Timestamp when session was created
        updated_at: Timestamp of last session update

    Schema:
        CREATE TABLE sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            session_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """

    __tablename__ = "sessions"

    session_id: str = Field(
        primary_key=True, max_length=255, description="Unique session identifier"
    )

    session_type: str = Field(
        max_length=50, description="Type of session (e.g., 'AGENT', 'MULTI_AGENT')"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session creation timestamp"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class AgentDB(SQLModel, table=True):
    """
    Agent database model for Strands Agents.

    Maps to the 'agents' table in PostgreSQL.
    Stores agent state, conversation manager state, and internal state as JSONB.

    Attributes:
        session_id: Foreign key to sessions table (part of composite PRIMARY KEY)
        agent_id: Agent identifier (part of composite PRIMARY KEY)
        state: Agent state stored as JSONB
        conversation_manager_state: Conversation manager state stored as JSONB
        internal_state: Internal agent state stored as JSONB (nullable)
        created_at: Timestamp when agent was created
        updated_at: Timestamp of last agent update

    Schema:
        CREATE TABLE agents (
            session_id VARCHAR(255) NOT NULL,
            agent_id VARCHAR(255) NOT NULL,
            state JSONB NOT NULL DEFAULT '{}',
            conversation_manager_state JSONB NOT NULL DEFAULT '{}',
            _internal_state JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            PRIMARY KEY (session_id, agent_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );
    """

    __tablename__ = "agents"

    # Composite primary key (session_id, agent_id)
    session_id: str = Field(
        max_length=255,
        description="Associated session ID",
        sa_column=Column(ForeignKey("sessions.session_id", ondelete="CASCADE"), primary_key=True),
    )

    agent_id: str = Field(primary_key=True, max_length=255, description="Unique agent identifier")

    # JSONB fields for agent state
    state: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Agent state as JSON"
    )

    conversation_manager_state: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Conversation manager state as JSON",
    )

    internal_state: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column("_internal_state", JSON, nullable=True),
        description="Internal agent state as JSON",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Agent creation timestamp"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class MessageDB(SQLModel, table=True):
    """
    Message database model for Strands Agents.

    Maps to the 'messages' table in PostgreSQL.
    Stores conversation messages with optional redaction support.

    Attributes:
        session_id: Foreign key to sessions table (part of composite PRIMARY KEY)
        agent_id: Foreign key to agents table (part of composite PRIMARY KEY)
        message_id: Sequential message identifier (part of composite PRIMARY KEY)
        message: Message content stored as JSONB
        redact_message: Redacted message content stored as JSONB (nullable)
        created_at: Timestamp when message was created
        updated_at: Timestamp of last message update

    Schema:
        CREATE TABLE messages (
            session_id VARCHAR(255) NOT NULL,
            agent_id VARCHAR(255) NOT NULL,
            message_id INTEGER NOT NULL,
            message JSONB NOT NULL,
            redact_message JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            PRIMARY KEY (session_id, agent_id, message_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (session_id, agent_id) REFERENCES agents(session_id, agent_id) ON DELETE CASCADE
        );
    """

    __tablename__ = "messages"

    # Composite primary key (session_id, agent_id, message_id)
    session_id: str = Field(
        max_length=255,
        description="Associated session ID",
        sa_column=Column(ForeignKey("sessions.session_id", ondelete="CASCADE"), primary_key=True),
    )

    agent_id: str = Field(primary_key=True, max_length=255, description="Associated agent ID")

    message_id: int = Field(
        primary_key=True, description="Sequential message ID within session/agent"
    )

    # JSONB fields for message content
    message: Dict[str, Any] = Field(sa_column=Column(JSON), description="Message content as JSON")

    redact_message: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Redacted message content as JSON (optional)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Message creation timestamp"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
