# Running Tests

This directory contains unit and integration tests for `strands-postgresql-session-manager`.

## Test Structure

```
tests/
├── test_unit.py          # Fast unit tests (no PostgreSQL required)
├── test_integration.py   # Integration tests (requires PostgreSQL)
└── README.md            # This file
```

## Prerequisites

### Install Dependencies

```bash
# Install package with dev dependencies
pip install -e ".[dev]"
```

### For Integration Tests Only

Start a PostgreSQL container:

```bash
docker run -d \
  --name postgres-test \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_USER=test \
  -e POSTGRES_DB=test \
  postgres:14
```

Set the database URL:

```bash
export DATABASE_URL="postgresql://test:test@localhost:5432/test"
```

## Running Tests

### Unit Tests Only (Fast, No Database Required)

```bash
pytest tests/test_unit.py -v
```

### Integration Tests (Requires PostgreSQL)

```bash
export DATABASE_URL="postgresql://test:test@localhost:5432/test"
pytest tests/test_integration.py -v
```

### All Tests

```bash
export DATABASE_URL="postgresql://test:test@localhost:5432/test"
pytest tests/ -v
```

### With Coverage

```bash
pytest tests/ --cov=src/strands_postgresql_session_manager --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Test Categories

### Unit Tests (`test_unit.py`)
- Uses in-memory SQLite database
- Tests all CRUD operations
- Tests CASCADE delete behavior
- Fast execution (~1-2 seconds)
- No external dependencies

### Integration Tests (`test_integration.py`)
- Uses real PostgreSQL database
- Tests complete agent workflows
- Tests concurrent sessions
- Tests JSONB storage with complex data
- Tests performance with 1000+ messages
- Slower execution (~10-30 seconds)

## Cleanup

After running integration tests:

```bash
# Stop and remove PostgreSQL container
docker stop postgres-test
docker rm postgres-test

# Or just stop it to preserve data
docker stop postgres-test
```

## Continuous Integration

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs:
- Unit tests on every push
- Integration tests on pull requests
- Coverage reporting to Codecov

## Troubleshooting

### "Import 'pytest' could not be resolved"

Install dev dependencies:
```bash
pip install -e ".[dev]"
```

### "DATABASE_URL not set" (Integration Tests)

Set the environment variable:
```bash
export DATABASE_URL="postgresql://test:test@localhost:5432/test"
```

### "Connection refused" (Integration Tests)

Ensure PostgreSQL container is running:
```bash
docker ps | grep postgres-test
```

If not running:
```bash
docker start postgres-test
```

### Tests are slow

Run only unit tests for fast feedback:
```bash
pytest tests/test_unit.py -v
```
