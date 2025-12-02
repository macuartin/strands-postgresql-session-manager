"""
Integration tests for PostgresSessionManager.

These tests require a real PostgreSQL database running.

Setup:
    docker run -d \\
        --name postgres-test \\
        -p 5432:5432 \\
        -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_USER=test \\
        -e POSTGRES_DB=test \\
        postgres:14

Run tests:
    pytest tests/test_integration.py -v

Cleanup:
    docker stop postgres-test && docker rm postgres-test
"""
import pytest
import os
from datetime import datetime
from sqlmodel import create_engine, SQLModel, Session, text
from unittest.mock import MagicMock

from strands_postgresql_session_manager import (
    PostgresSessionManager,
    SessionDB,
    AgentDB,
    MessageDB,
)


# Skip integration tests if DATABASE_URL not set
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set. Run: export DATABASE_URL='postgresql://test:test@localhost:5432/test'"
)


@pytest.fixture(scope="session")
def engine():
    """Create a real PostgreSQL engine for integration testing."""
    database_url = os.getenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    engine = create_engine(database_url, echo=True)
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup: drop all tables
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def cleanup_database(engine):
    """Clean up database between tests."""
    yield
    
    # Clear all data after each test (use text() for raw SQL)
    with Session(engine) as session:
        session.exec(text("DELETE FROM messages"))
        session.exec(text("DELETE FROM agents"))
        session.exec(text("DELETE FROM sessions"))
        session.commit()


@pytest.fixture
def session_manager(engine):
    """Create a PostgresSessionManager with real PostgreSQL."""
    return PostgresSessionManager(
        session_id="integration_test_session",
        engine=engine
    )


class TestFullAgentWorkflow:
    """Test complete agent workflow from session creation to message processing."""
    
    def test_complete_agent_session_lifecycle(self, session_manager, engine):
        """Test creating session, agent, and multiple messages."""
        # 1. Create session
        mock_session = MagicMock()
        mock_session.session_id = "integration_test_session"
        mock_session.to_dict.return_value = {
            'session_id': 'integration_test_session',
            'session_type': 'AGENT',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        
        session_manager.create_session(mock_session)
        
        # Verify session exists
        with Session(engine) as db_session:
            session_db = db_session.get(SessionDB, "integration_test_session")
            assert session_db is not None
        
        # 2. Create agent
        mock_agent = MagicMock()
        mock_agent.agent_id = "main_agent"
        mock_agent.to_dict.return_value = {
            'agent_id': 'main_agent',
            'state': {'counter': 0},
            'conversation_manager_state': {'turn': 0, 'messages': []},
            '_internal_state': {},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        
        session_manager.create_agent("integration_test_session", mock_agent)
        
        # Verify agent exists
        with Session(engine) as db_session:
            agent_db = db_session.get(
                AgentDB,
                {"session_id": "integration_test_session", "agent_id": "main_agent"}
            )
            assert agent_db is not None
        
        # 3. Add messages simulating conversation
        for i in range(1, 6):
            mock_message = MagicMock()
            mock_message.message_id = i
            mock_message.to_dict.return_value = {
                'message_id': i,
                'message': {
                    'role': 'user' if i % 2 == 1 else 'assistant',
                    'content': [{'type': 'text', 'text': f'Message {i}'}]
                },
                'redact_message': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            
            session_manager.create_message("integration_test_session", "main_agent", mock_message)
        
        # Verify messages
        messages = session_manager.list_messages("integration_test_session", "main_agent")
        assert len(messages) == 5
        
        # 4. Update agent state after conversation
        mock_agent.to_dict.return_value = {
            'agent_id': 'main_agent',
            'state': {'counter': 5},  # Updated state
            'conversation_manager_state': {'turn': 5, 'messages': list(range(1, 6))},
            '_internal_state': {},
            'updated_at': datetime.utcnow(),
        }
        
        session_manager.update_agent("integration_test_session", mock_agent)
        
        # Verify agent update
        with Session(engine) as db_session:
            agent_db = db_session.get(
                AgentDB,
                {"session_id": "integration_test_session", "agent_id": "main_agent"}
            )
            assert agent_db.state['counter'] == 5
        
        # 5. Delete session (should cascade)
        result = session_manager.delete_session("integration_test_session")
        assert result is True
        
        # Verify everything is gone
        with Session(engine) as db_session:
            session_db = db_session.get(SessionDB, "integration_test_session")
            agent_db = db_session.get(
                AgentDB,
                {"session_id": "integration_test_session", "agent_id": "main_agent"}
            )
            messages = session_manager.list_messages("integration_test_session", "main_agent")
            
            assert session_db is None
            assert agent_db is None
            assert len(messages) == 0


class TestConcurrentSessions:
    """Test handling multiple concurrent sessions."""
    
    def test_multiple_sessions_isolation(self, engine):
        """Test that multiple sessions don't interfere with each other."""
        # Create two session managers
        sm1 = PostgresSessionManager(session_id="session_1", engine=engine)
        sm2 = PostgresSessionManager(session_id="session_2", engine=engine)
        
        # Create sessions
        for sm, sid in [(sm1, "session_1"), (sm2, "session_2")]:
            mock_session = MagicMock()
            mock_session.session_id = sid
            mock_session.to_dict.return_value = {
                'session_id': sid,
                'session_type': 'AGENT',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            sm.create_session(mock_session)
            
            # Create agent
            mock_agent = MagicMock()
            mock_agent.agent_id = "agent_main"
            mock_agent.to_dict.return_value = {
                'agent_id': 'agent_main',
                'state': {'session_specific': sid},
                'conversation_manager_state': {},
                '_internal_state': {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            sm.create_agent(sid, mock_agent)
        
        # Verify both sessions exist independently
        with Session(engine) as db_session:
            session_1 = db_session.get(SessionDB, "session_1")
            session_2 = db_session.get(SessionDB, "session_2")
            
            agent_1 = db_session.get(AgentDB, {"session_id": "session_1", "agent_id": "agent_main"})
            agent_2 = db_session.get(AgentDB, {"session_id": "session_2", "agent_id": "agent_main"})
            
            assert session_1 is not None
            assert session_2 is not None
            assert agent_1.state['session_specific'] == "session_1"
            assert agent_2.state['session_specific'] == "session_2"
        
        # Delete session_1 should not affect session_2
        sm1.delete_session("session_1")
        
        with Session(engine) as db_session:
            session_1 = db_session.get(SessionDB, "session_1")
            session_2 = db_session.get(SessionDB, "session_2")
            
            assert session_1 is None
            assert session_2 is not None


class TestJSONBStorage:
    """Test JSONB column storage and retrieval."""
    
    def test_complex_state_storage(self, session_manager, engine):
        """Test storing complex nested JSON structures."""
        # Create session
        mock_session = MagicMock()
        mock_session.session_id = "integration_test_session"
        mock_session.to_dict.return_value = {
            'session_id': 'integration_test_session',
            'session_type': 'AGENT',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        session_manager.create_session(mock_session)
        
        # Create agent with complex state
        complex_state = {
            'user_data': {
                'name': 'Test User',
                'preferences': {
                    'language': 'es',
                    'timezone': 'America/Mexico_City',
                    'notifications': True,
                }
            },
            'workflow': {
                'current_step': 3,
                'steps_completed': [1, 2, 3],
                'pending_actions': ['approve', 'review'],
            },
            'metrics': {
                'messages_sent': 42,
                'average_response_time': 1.5,
            }
        }
        
        mock_agent = MagicMock()
        mock_agent.agent_id = "agent_main"
        mock_agent.to_dict.return_value = {
            'agent_id': 'agent_main',
            'state': complex_state,
            'conversation_manager_state': {},
            '_internal_state': {},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        
        session_manager.create_agent("integration_test_session", mock_agent)
        
        # Retrieve and verify state
        with Session(engine) as db_session:
            agent_db = db_session.get(
                AgentDB,
                {"session_id": "integration_test_session", "agent_id": "agent_main"}
            )
            
            assert agent_db.state == complex_state
            assert agent_db.state['user_data']['preferences']['language'] == 'es'
            assert agent_db.state['workflow']['steps_completed'] == [1, 2, 3]
            assert agent_db.state['metrics']['messages_sent'] == 42


class TestPerformance:
    """Test performance with larger datasets."""
    
    def test_large_message_volume(self, session_manager, engine):
        """Test handling 1000+ messages in a single session."""
        # Create session and agent
        mock_session = MagicMock()
        mock_session.session_id = "integration_test_session"
        mock_session.to_dict.return_value = {
            'session_id': 'integration_test_session',
            'session_type': 'AGENT',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        session_manager.create_session(mock_session)
        
        mock_agent = MagicMock()
        mock_agent.agent_id = "agent_main"
        mock_agent.to_dict.return_value = {
            'agent_id': 'agent_main',
            'state': {},
            'conversation_manager_state': {},
            '_internal_state': {},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        session_manager.create_agent("integration_test_session", mock_agent)
        
        # Insert 1000 messages
        num_messages = 1000
        for i in range(1, num_messages + 1):
            mock_message = MagicMock()
            mock_message.message_id = i
            mock_message.to_dict.return_value = {
                'message_id': i,
                'message': {
                    'role': 'user' if i % 2 == 1 else 'assistant',
                    'content': [{'type': 'text', 'text': f'Performance test message {i}'}]
                },
                'redact_message': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
            session_manager.create_message("integration_test_session", "agent_main", mock_message)
        
        # Verify count
        messages = session_manager.list_messages("integration_test_session", "agent_main")
        assert len(messages) == num_messages
        
        # Test pagination
        page_1 = session_manager.list_messages("integration_test_session", "agent_main", limit=100, offset=0)
        page_2 = session_manager.list_messages("integration_test_session", "agent_main", limit=100, offset=100)
        
        assert len(page_1) == 100
        assert len(page_2) == 100
        assert page_1[0].message_id != page_2[0].message_id
