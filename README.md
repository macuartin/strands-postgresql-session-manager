# Strands PostgreSQL Session Manager

[![Awesome Strands Agents](https://img.shields.io/badge/Awesome-Strands%20Agents-00FF77?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjkwIiBoZWlnaHQ9IjQ2MyIgdmlld0JveD0iMCAwIDI5MCA0NjMiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik05Ny4yOTAyIDUyLjc4ODRDODUuMDY3NCA0OS4xNjY3IDcyLjIyMzQgNTYuMTM4OSA2OC42MDE3IDY4LjM2MTZDNjQuOTgwMSA4MC41ODQzIDcxLjk1MjQgOTMuNDI4MyA4NC4xNzQ5IDk3LjA1MDFMMjM1LjExNyAxMzkuNzc1QzI0NS4yMjMgMTQyLjc2OSAyNDYuMzU3IDE1Ni42MjggMjM2Ljg3NCAxNjEuMjI2TDMyLjU0NiAyNjAuMjkxQy0xNC45NDM5IDI4My4zMTYgLTkuMTYxMDcgMzUyLjc0IDQxLjQ4MzUgMzY3LjU5MUwxODkuNTUxIDQxMS4wMDlMMTkwLjEyNSA0MTEuMTY5QzIwMi4xODMgNDE0LjM3NiAyMTQuNjY1IDQwNy4zOTYgMjE4LjE5NiAzOTUuMzU1QzIyMS43ODQgMzgzLjEyMiAyMTQuNzc0IDM3MC4yOTYgMjAyLjU0MSAzNjYuNzA5TDU0LjQ3MzggMzIzLjI5MUM0NC4zNDQ3IDMyMC4zMjEgNDMuMTg3OSAzMDYuNDM2IDUyLjY4NTcgMzAxLjgzMUwyNTcuMDE0IDIwMi43NjZDMzA0LjQzMiAxNzkuNzc2IDI5OC43NTggMTEwLjQ4MyAyNDguMjMzIDk1LjUxMkw5Ny4yOTAyIDUyLjc4ODRaIiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik0yNTkuMTQ3IDAuOTgxODEyQzI3MS4zODkgLTIuNTc0OTggMjg0LjE5NyA0LjQ2NTcxIDI4Ny43NTQgMTYuNzA3NEMyOTEuMzExIDI4Ljk0OTIgMjg0LjI3IDQxLjc1NyAyNzIuMDI4IDQ1LjMxMzhMNzEuMTcyNyAxMDMuNjcxQzQwLjcxNDIgMTEyLjUyMSAzNy4xOTc2IDE1NC4yNjIgNjUuNzQ1OSAxNjguMDgzTDI0MS4zNDMgMjUzLjA5M0MzMDcuODcyIDI4NS4zMDIgMjk5Ljc5NCAzODIuNTQ2IDIyOC44NjIgNDAzLjMzNkwzMC40MDQxIDQ2MS41MDJDMTguMTcwNyA0NjUuMDg4IDUuMzQ3MDggNDU4LjA3OCAxLjc2MTUzIDQ0NS44NDRDLTEuODIzOSA0MzMuNjExIDUuMTg2MzcgNDIwLjc4NyAxNy40MTk3IDQxNy4yMDJMMjE1Ljg3OCAzNTkuMDM1QzI0Ni4yNzcgMzUwLjEyNSAyNDkuNzM5IDMwOC40NDkgMjIxLjIyNiAyOTQuNjQ1TDQ1LjYyOTcgMjA5LjYzNUMtMjAuOTgzNCAxNzcuMzg2IC0xMi43NzcyIDc5Ljk4OTMgNTguMjkyOCA1OS4zNDAyTDI1OS4xNDcgMC45ODE4MTJaIiBmaWxsPSIjRkZGRkZGIi8+Cjwvc3ZnPgo=&logoColor=white)](https://github.com/cagataycali/awesome-strands-agents)

A production-ready session manager for [Strands Agents](https://strandsagents.com/) that uses PostgreSQL for persistent storage. This enables agents to maintain conversation history and state with full ACID guarantees, even in distributed environments.

Tested with PostgreSQL 14+ (local, RDS, Cloud SQL, Azure Database, and Supabase).

## Features

- **Persistent Sessions**: Store agent conversations and state in PostgreSQL with full ACID guarantees
- **Distributed Ready**: Share sessions across multiple application instances
- **JSONB Storage**: Native JSON support for complex data structures (state, conversation manager, messages)
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

# Create tables (run once)
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

## Storage Structure

The PostgresSessionManager stores data using the following table structure:

```
sessions (session_id PK, session_type, created_at, updated_at)
    └── agents (session_id FK, agent_id, state JSONB, conversation_manager_state JSONB, _internal_state JSONB)
        └── messages (session_id FK, agent_id, message_id, message JSONB, redact_message JSONB)
```

Foreign keys use `ON DELETE CASCADE` to ensure referential integrity.

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
- strands-agents >= 1.0.0
- sqlmodel >= 0.0.14
- psycopg2-binary >= 2.9.0

## License

MIT License - see [LICENSE](LICENSE) for details.
