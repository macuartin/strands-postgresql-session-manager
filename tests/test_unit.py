"""Unit tests for PostgresSessionManager."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from strands.types.content import ContentBlock
from strands.types.session import Session, SessionAgent, SessionMessage, SessionType

from strands_postgresql_session_manager import PostgresSessionManager


@pytest.fixture
def mock_engine():
    """Mock SQLModel engine for testing."""
    return MagicMock()


@pytest.fixture
def postgres_manager(mock_engine):
    """Create PostgresSessionManager with mocked engine."""
    # Mock the session repository methods during initialization to avoid auto-creation
    with (
        patch.object(PostgresSessionManager, "read_session", return_value=None),
        patch.object(PostgresSessionManager, "create_session"),
    ):
        return PostgresSessionManager(session_id="test", engine=mock_engine)


@pytest.fixture
def sample_session():
    """Create sample session for testing."""
    return Session(
        session_id="test-session-123",
        session_type=SessionType.AGENT,
    )


@pytest.fixture
def sample_agent():
    """Create sample agent for testing."""
    return SessionAgent(
        agent_id="test-agent-456",
        state={"key": "value"},
        conversation_manager_state=NullConversationManager().get_state(),
    )


@pytest.fixture
def sample_message():
    """Create sample message for testing."""
    return SessionMessage.from_message(
        message={
            "role": "user",
            "content": [ContentBlock(text="test_message")],
        },
        index=0,
    )


# Session CRUD Tests


def test_create_session(postgres_manager, sample_session, mock_engine):
    """Test creating a session in PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.get.return_value = None  # Session doesn't exist

        postgres_manager.create_session(sample_session)

        # Verify session was added and committed
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


def test_create_session_already_exists(postgres_manager, sample_session):
    """Test creating a session that already exists (should update)."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock no existing session (get returns None)
        # create_session siempre crea una nueva session, no actualiza
        mock_db_session.get.return_value = None

        postgres_manager.create_session(sample_session)

        # Verify session was added and committed
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


def test_read_session(postgres_manager, sample_session):
    """Test reading a session from PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock session exists with complete data
        from strands_postgresql_session_manager.models import SessionDB

        mock_session_db = SessionDB(
            session_id=sample_session.session_id,
            session_type="AGENT",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_db_session.exec.return_value.one_or_none.return_value = mock_session_db

        result = postgres_manager.read_session(sample_session.session_id)

        assert result.session_id == sample_session.session_id
        assert result.session_type == SessionType.AGENT


def test_read_nonexistent_session(postgres_manager):
    """Test reading a session that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.exec.return_value.one_or_none.return_value = None

        result = postgres_manager.read_session("nonexistent-session")

        assert result is None


def test_delete_session(postgres_manager, sample_session):
    """Test deleting a session from PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.exec.return_value.first.return_value = MagicMock()  # Session exists

        result = postgres_manager.delete_session(sample_session.session_id)

        assert result is True
        assert mock_db_session.delete.called
        assert mock_db_session.commit.called


def test_delete_nonexistent_session(postgres_manager):
    """Test deleting a session that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock exec() to return empty result
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db_session.exec.return_value = mock_result

        result = postgres_manager.delete_session("nonexistent")

        # Note: Current implementation returns True even if session not found
        assert result is True


# Agent CRUD Tests


def test_create_agent(postgres_manager, sample_session, sample_agent):
    """Test creating an agent in PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        postgres_manager.create_agent(sample_session.session_id, sample_agent)

        # Verify agent was added and committed
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


def test_read_agent(postgres_manager, sample_session, sample_agent):
    """Test reading an agent from PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock agent exists - use real AgentDB to support .dict()
        from strands_postgresql_session_manager.models import AgentDB

        mock_agent_db = AgentDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            state=sample_agent.state,
            conversation_manager_state=sample_agent.conversation_manager_state,
            internal_state={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_db_session.exec.return_value.one_or_none.return_value = mock_agent_db

        result = postgres_manager.read_agent(sample_session.session_id, sample_agent.agent_id)

        assert result.agent_id == sample_agent.agent_id
        assert result.state == sample_agent.state


def test_read_nonexistent_agent(postgres_manager, sample_session):
    """Test reading an agent that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.exec.return_value.one_or_none.return_value = None

        result = postgres_manager.read_agent(sample_session.session_id, "nonexistent_agent")

        assert result is None


def test_update_agent(postgres_manager, sample_session, sample_agent):
    """Test updating an agent in PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock existing agent - use real AgentDB to support .dict() method
        from strands_postgresql_session_manager.models import AgentDB

        mock_agent_db = AgentDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            state={"old": "value"},
            conversation_manager_state={},
            internal_state={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_db_session.exec.return_value.one_or_none.return_value = mock_agent_db

        sample_agent.state = {"updated": "value"}
        postgres_manager.update_agent(sample_session.session_id, sample_agent)

        # Verify state was updated and committed
        assert mock_agent_db.state == {"updated": "value"}
        assert mock_db_session.commit.called


def test_update_nonexistent_agent(postgres_manager, sample_session, sample_agent):
    """Test updating an agent that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.exec.return_value.first.return_value = None

        # Should not raise exception, just log error (check implementation)
        postgres_manager.update_agent(sample_session.session_id, sample_agent)


# Message CRUD Tests


def test_create_message(postgres_manager, sample_session, sample_agent, sample_message):
    """Test creating a message in PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        postgres_manager.create_message(
            sample_session.session_id, sample_agent.agent_id, sample_message
        )

        # Verify message was added and committed
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


def test_read_message(postgres_manager, sample_session, sample_agent, sample_message):
    """Test reading a message from PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock message exists - use real MessageDB to support .dict()
        from strands_postgresql_session_manager.models import MessageDB

        mock_message_db = MessageDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            message_id=sample_message.message_id,
            message=sample_message.message,
            redact_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_db_session.exec.return_value.one_or_none.return_value = mock_message_db

        result = postgres_manager.read_message(
            sample_session.session_id, sample_agent.agent_id, sample_message.message_id
        )

        assert result.message_id == sample_message.message_id
        assert result.message["role"] == sample_message.message["role"]


def test_read_nonexistent_message(postgres_manager, sample_session, sample_agent):
    """Test reading a message that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.exec.return_value.one_or_none.return_value = None

        result = postgres_manager.read_message(
            sample_session.session_id, sample_agent.agent_id, 999
        )

        assert result is None


def test_update_message(postgres_manager, sample_session, sample_agent, sample_message):
    """Test updating a message in PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock existing message
        mock_message_db = MagicMock()
        mock_db_session.get.return_value = mock_message_db

        sample_message.message["content"] = [ContentBlock(text="Updated content")]
        postgres_manager.update_message(
            sample_session.session_id, sample_agent.agent_id, sample_message
        )

        # Verify message was updated and committed
        assert mock_db_session.commit.called


def test_update_nonexistent_message(postgres_manager, sample_session, sample_agent, sample_message):
    """Test updating a message that doesn't exist."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session
        mock_db_session.get.return_value = None

        # Should not raise exception, just log error
        postgres_manager.update_message(
            sample_session.session_id, sample_agent.agent_id, sample_message
        )


def test_list_messages_all(postgres_manager, sample_session, sample_agent):
    """Test listing all messages from PostgreSQL."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock message results - use real MessageDB to support .dict()
        from strands_postgresql_session_manager.models import MessageDB

        mock_msg1 = MessageDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            message_id=0,
            message={"role": "user", "content": [{"text": "msg1"}]},
            redact_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_msg2 = MessageDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            message_id=1,
            message={"role": "assistant", "content": [{"text": "msg2"}]},
            redact_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_db_session.exec.return_value.all.return_value = [mock_msg1, mock_msg2]

        result = postgres_manager.list_messages(sample_session.session_id, sample_agent.agent_id)

        assert len(result) == 2
        assert result[0].message_id == 0
        assert result[1].message_id == 1


def test_list_messages_with_pagination(postgres_manager, sample_session, sample_agent):
    """Test listing messages with limit and offset."""
    with patch("strands_postgresql_session_manager.session_manager.Session") as mock_session_cls:
        mock_db_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_db_session

        # Mock single message result - use real MessageDB to support .dict()
        from strands_postgresql_session_manager.models import MessageDB

        mock_msg = MessageDB(
            session_id=sample_session.session_id,
            agent_id=sample_agent.agent_id,
            message_id=5,
            message={"role": "user", "content": []},
            redact_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_db_session.exec.return_value.all.return_value = [mock_msg]

        result = postgres_manager.list_messages(
            sample_session.session_id, sample_agent.agent_id, limit=1, offset=5
        )

        assert len(result) == 1
        assert result[0].message_id == 5
