# Strands PostgreSQL Session Manager

[![PyPI version](https://badge.fury.io/py/strands-postgresql-session-manager.svg)](https://pypi.org/project/strands-postgresql-session-manager/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A high-performance PostgreSQL session manager for [Strands Agents SDK](https://strandsagents.com/) that provides persistent storage with full ACID guarantees, CASCADE deletes, and JSONB support for flexible state management.

## Why PostgreSQL for Session Storage?

While in-memory solutions like Redis/Valkey excel at speed, PostgreSQL offers unique advantages for production agent systems:

- **✅ Full ACID Guarantees** - No message is ever lost, even on crashes
- **✅ Complex Queries & Analytics** - SQL enables deep conversation analysis
- **✅ Compliance & Audit Trails** - Persistent logs for regulatory requirements
- **✅ Existing Infrastructure** - Most enterprises already run PostgreSQL
- **✅ Referential Integrity** - CASCADE deletes ensure data consistency
- **✅ Cost-Effective Storage** - Disk storage cheaper than RAM for long conversations
- **✅ Full-Text Search** - Built-in capabilities for semantic search

## Installation

```bash
pip install strands-postgresql-session-manager
```

## Quick Start

### 1. Create Database Tables

```python
from sqlmodel import create_engine, SQLModel
from strands_postgresql_session_manager import SessionDB, AgentDB, MessageDB

# Create engine
engine = create_engine("postgresql://user:password@localhost:5432/agents_db")

# Create tables (run once)
SQLModel.metadata.create_all(engine)
```

### 2. Use with Strands Agent

```python
from strands import Agent
from strands_postgresql_session_manager import PostgresSessionManager
from sqlmodel import create_engine

# Create PostgreSQL engine
engine = create_engine("postgresql://user:password@localhost:5432/agents_db")

# Create session manager with unique session ID
session_manager = PostgresSessionManager(
    session_id="user_123",
    engine=engine
)

# Create agent with session manager
agent = Agent(session_manager=session_manager)

# Use agent - all messages are automatically persisted
agent("Hello! Tell me about PostgreSQL session storage.")

# Conversation is now stored in PostgreSQL with ACID guarantees
```

### 3. Resume Conversations

```python
# Later, resume the same conversation using the same session_id
session_manager = PostgresSessionManager(
    session_id="user_123",  # Same ID as before
    engine=engine
)

agent = Agent(session_manager=session_manager)

# Agent automatically loads full conversation history
agent("What was the last thing we discussed?")
```

## Key Features

- **🔒 ACID Transactions** - Full consistency guarantees for all operations
- **🗄️ JSONB Storage** - Flexible schema for agent state and messages
- **🔗 CASCADE Deletes** - Deleting a session automatically removes all agents and messages
- **📊 SQL Analytics** - Query conversation history with powerful SQL
- **⚡ Connection Pooling** - Efficient database connection management
- **🔍 Indexable Data** - Fast lookups on session_id, agent_id, timestamps
- **🛡️ Type-Safe** - Full type hints for IDE autocompletion
- **📝 Detailed Logging** - Comprehensive logging for debugging

## Configuration

### Basic Configuration

```python
from sqlmodel import create_engine
from strands_postgresql_session_manager import PostgresSessionManager

# Simple configuration
engine = create_engine("postgresql://user:pass@localhost:5432/db")
session_manager = PostgresSessionManager(
    session_id="unique_session_id",
    engine=engine
)
```

### Production Configuration

```python
from sqlmodel import create_engine
from strands_postgresql_session_manager import PostgresSessionManager
import logging

# Production engine with connection pooling
engine = create_engine(
    "postgresql://user:pass@localhost:5432/agents_db",
    pool_size=20,              # Connection pool size
    max_overflow=10,           # Additional connections when pool is full
    pool_pre_ping=True,        # Verify connections before using
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False,                # Disable SQL echo in production
)

# Custom logger
logger = logging.getLogger("my_app.sessions")

# Create session manager with custom logger
session_manager = PostgresSessionManager(
    session_id="user_456",
    engine=engine,
    logger=logger
)
```

### Environment-Based Configuration

```python
import os
from sqlmodel import create_engine
from strands_postgresql_session_manager import PostgresSessionManager

# Load from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:pass@localhost:5432/agents_db"
)

engine = create_engine(DATABASE_URL)
session_manager = PostgresSessionManager(
    session_id=f"user_{user_id}",
    engine=engine
)
```

## Storage Structure

The PostgresSessionManager uses three tables with the following structure:

### Sessions Table

```sql
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    session_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Agents Table

```sql
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
```

### Messages Table

```sql
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
    FOREIGN KEY (session_id, agent_id) 
        REFERENCES agents(session_id, agent_id) ON DELETE CASCADE
);
```

## Available Methods

The following methods are used transparently by Strands Agents SDK:

### Session Methods
- `create_session(session)` - Create a new session
- `read_session(session_id)` - Retrieve session data
- `update_session(session)` - Update session metadata
- `delete_session(session_id)` - Remove session and all associated data (CASCADE)

### Agent Methods
- `create_agent(session_id, agent)` - Store agent in session
- `read_agent(session_id, agent_id)` - Retrieve agent data
- `update_agent(session_id, agent)` - Update agent state
- `delete_agent(agent_id)` - Remove agent
- `list_agents(session_id)` - List all agents in a session

### Message Methods
- `create_message(session_id, agent_id, message)` - Store message
- `read_message(session_id, agent_id, message_id)` - Retrieve message
- `update_message(session_id, agent_id, message)` - Update message
- `delete_message(message_id)` - Remove message
- `list_messages(session_id, agent_id, limit, offset)` - List messages with pagination

## Advanced Usage

### Custom Models

You can provide custom SQLModel classes for specialized use cases:

```python
from strands_postgresql_session_manager import PostgresSessionManager, SessionDB
from sqlmodel import Field

class CustomSessionDB(SessionDB):
    """Extended session model with additional fields"""
    organization_id: str = Field(index=True)
    tags: dict = Field(default_factory=dict, sa_column=Column(JSON))

session_manager = PostgresSessionManager(
    session_id="user_789",
    engine=engine,
    session_model=CustomSessionDB  # Use custom model
)
```

### Analytics Queries

```python
from sqlmodel import Session, select, func
from strands_postgresql_session_manager.models import MessageDB

with Session(engine) as db_session:
    # Count messages per session
    statement = (
        select(MessageDB.session_id, func.count(MessageDB.message_id))
        .group_by(MessageDB.session_id)
    )
    results = db_session.exec(statement).all()
    
    # Find sessions with most activity
    active_sessions = [
        (session_id, count) 
        for session_id, count in results 
        if count > 100
    ]
```

### Cleanup Old Sessions

```python
from datetime import datetime, timedelta
from sqlmodel import Session, select
from strands_postgresql_session_manager.models import SessionDB

# Delete sessions older than 90 days
cutoff_date = datetime.utcnow() - timedelta(days=90)

with Session(engine) as db_session:
    old_sessions = db_session.exec(
        select(SessionDB).where(SessionDB.updated_at < cutoff_date)
    ).all()
    
    for session in old_sessions:
        db_session.delete(session)  # CASCADE deletes agents and messages
    
    db_session.commit()
```

## Requirements

- **Python**: 3.10 or higher
- **PostgreSQL**: 12.0 or higher
- **Dependencies**:
  - `strands-agents >= 1.0.0`
  - `sqlmodel >= 0.0.14`
  - `psycopg2-binary >= 2.9.0` (or `psycopg2`)

## Performance Considerations

### Indexing

For optimal performance with large datasets, add indexes:

```sql
-- Index on message timestamps for time-based queries
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Index on session updated_at for cleanup queries
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at);
```

### Connection Pooling

Always use connection pooling in production:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Adjust based on concurrent users
    max_overflow=10,
    pool_pre_ping=True,     # Prevents stale connections
)
```

### JSONB Performance

PostgreSQL JSONB is indexed and queryable:

```sql
-- Query messages containing specific text
SELECT * FROM messages 
WHERE message @> '{"role": "user"}';

-- Create GIN index for JSONB queries
CREATE INDEX idx_messages_content ON messages USING GIN (message);
```

## Comparison with Other Session Managers

| Feature | PostgreSQL | Valkey/Redis | File Storage |
|---------|-----------|--------------|--------------|
| **Persistence** | ✅ ACID guaranteed | ⚠️ Optional (AOF/RDB) | ✅ File-based |
| **Latency** | 5-20ms | < 1ms | < 1ms |
| **Durability** | ✅ Full ACID | ⚠️ Eventually consistent | ✅ Synchronous |
| **Scalability** | ✅ Read replicas | ✅ Clustering | ❌ Single machine |
| **Query Power** | ✅ Full SQL | ❌ Limited | ❌ None |
| **Cost** | $ Disk storage | $$$ Memory | Free |
| **Best For** | Production, compliance, analytics | High-performance caching | Development, testing |

## Troubleshooting

### Connection Issues

```python
# Test database connection
from sqlmodel import create_engine, text

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Table Creation

```python
# Verify tables exist
from sqlmodel import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Existing tables: {tables}")

# Create missing tables
if "sessions" not in tables:
    SQLModel.metadata.create_all(engine)
```

## Contributing

Contributions are welcome! Please open issues or submit pull requests on [GitHub](https://github.com/macuartin/strands-postgresql-session-manager).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## References

- **PyPI**: [strands-postgresql-session-manager](https://pypi.org/project/strands-postgresql-session-manager/)
- **GitHub**: [macuartin/strands-postgresql-session-manager](https://github.com/macuartin/strands-postgresql-session-manager)
- **Issues**: [Report bugs or feature requests](https://github.com/macuartin/strands-postgresql-session-manager/issues)
- **Strands Agents**: [https://strandsagents.com](https://strandsagents.com)

---

**Built with ❤️ for the Strands Agents community**
