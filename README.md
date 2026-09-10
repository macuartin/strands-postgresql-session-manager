# Strands PostgreSQL Session Manager

A production-ready session manager for [Strands Agents](https://strandsagents.com/) that uses PostgreSQL for persistent storage. This enables agents to maintain conversation history and state with full ACID guarantees, even in distributed environments.

Tested with Strands Agents 1.55.1 and PostgreSQL 14+ (local, RDS, Cloud SQL, Azure Database, and Supabase).

## Features

- **Persistent Sessions**: Store agent conversations and state in PostgreSQL with full ACID guarantees
- **Distributed Ready**: Share sessions across multiple application instances
- **JSONB Storage**: Native PostgreSQL JSONB support for complex data structures (state, conversation manager, messages)
- **Multi-agent State**: Persist Graph and Swarm execution state in PostgreSQL
- **Referential Integrity**: CASCADE deletes ensure data consistency
- **Production Tested**: Battle-tested with 18 unit tests + 4 integration tests (100% passing)
- **Analytics Ready**: SQL queries for conversation analysis and reporting

## Installation

```bash
pip install strands-postgresql-session-manager
```

## Quick Start

```python
from strands import Agent
from strands_postgresql_session_manager import PostgresSessionManager
from sqlmodel import create_engine, SQLModel

# Create PostgreSQL engine
engine = create_engine("postgresql://user:password@localhost:5432/agents_db")

# Create tables for a new database
SQLModel.metadata.create_all(engine)

# Create session manager with unique session ID
session_manager = PostgresSessionManager(
    session_id="user_123",
    engine=engine
)

# Create agent with session manager
agent = Agent(session_manager=session_manager)

# Use agent - all messages are automatically persisted to PostgreSQL
agent("Hello! Tell me about PostgreSQL session storage.")

# The conversation is now stored in PostgreSQL and can be resumed later,
# using the same session_id
```

For an existing `v0.1.0` database, install the migration extra and run the versioned migration before starting the application:

```bash
pip install 'strands-postgresql-session-manager[migrations]'
export DATABASE_URL="postgresql://user:password@localhost:5432/agents_db"
alembic -c alembic.ini upgrade head
```

The migration converts state columns to PostgreSQL JSONB, adds multi-agent state, and enforces message-to-agent cascade deletes.

## Storage Structure

The PostgresSessionManager stores data using the following table structure:

```
sessions (session_id PK, session_type, created_at, updated_at)
    └── agents (session_id FK, agent_id, state JSONB, conversation_manager_state JSONB, _internal_state JSONB)
        ├── messages (session_id FK, agent_id FK, message_id, message JSONB, redact_message JSONB)
    └── multi_agents (session_id FK, multi_agent_id, state JSONB)
```

Foreign keys use `ON DELETE CASCADE` to ensure referential integrity.

This package uses Strands' repository-based session API. Strands now recommends `SnapshotSessionManager` with the unified `Storage` protocol for new single-agent applications; use this package when you need PostgreSQL-backed record-level persistence or Graph/Swarm sessions.

## API Reference

### PostgresSessionManager

```python
PostgresSessionManager(
    session_id: str,
    engine: Engine
)
```

**Parameters:**

- `session_id`: Unique identifier for the session
- `engine`: Configured SQLAlchemy/SQLModel engine instance

**Methods** (Note that these methods are used transparently by Strands):

- `create_session(session)`: Create a new session
- `read_session(session_id)`: Retrieve session data
- `delete_session(session_id)`: Remove session and all associated data (CASCADE)
- `create_agent(session_id, agent)`: Store agent in session
- `read_agent(session_id, agent_id)`: Retrieve agent data
- `update_agent(session_id, agent)`: Update agent state
- `create_message(session_id, agent_id, message)`: Store message
- `read_message(session_id, agent_id, message_id)`: Retrieve message
- `update_message(session_id, agent_id, message)`: Update message
- `list_messages(session_id, agent_id, limit=None, offset=0)`: List all messages
- `create_multi_agent(session_id, multi_agent)`: Store Graph or Swarm state
- `read_multi_agent(session_id, multi_agent_id)`: Retrieve Graph or Swarm state
- `update_multi_agent(session_id, multi_agent)`: Update Graph or Swarm state

## Contributing

### Setup

```bash
# Clone the repository
git clone https://github.com/macuartin/strands-postgresql-session-manager
cd strands-postgresql-session-manager

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run unit tests only (default)
pytest tests/test_unit.py -v

# Run with coverage
pytest tests/test_unit.py --cov=src/strands_postgresql_session_manager --cov-report=html
```

### Integration Tests

Integration tests require a running PostgreSQL instance:

```bash
# Start PostgreSQL (Docker)
docker run -d --name postgres-test \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_USER=test \
  -e POSTGRES_DB=test \
  postgres:14

# Set DATABASE_URL
export DATABASE_URL="postgresql://test:test@localhost:5432/test"

# Run integration tests
pytest tests/test_integration.py -v

# Cleanup
docker stop postgres-test && docker rm postgres-test
```

## Requirements

- Python 3.10+
- PostgreSQL 14+
- strands-agents >= 1.0.0 (tested with 1.55.1)
- sqlmodel >= 0.0.14
- psycopg2-binary >= 2.9.0

## License

MIT License - see [LICENSE](LICENSE) for details.
