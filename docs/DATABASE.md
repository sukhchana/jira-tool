# Database Documentation

## Overview
The application uses SQLite for tracking execution plans and revisions. The database is stored at `data/execution_tracker.db`.

## Database Schema

### Executions Table
```sql
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY,
    epic_key TEXT NOT NULL,
    execution_plan_file TEXT NOT NULL,
    proposed_plan_file TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    parent_execution_id TEXT,
    FOREIGN KEY (parent_execution_id) REFERENCES executions (execution_id)
);
```

### Revisions Table
```sql
CREATE TABLE revisions (
    revision_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    proposed_plan_file TEXT NOT NULL,
    execution_plan_file TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    changes_requested TEXT NOT NULL,
    changes_interpreted TEXT NOT NULL,
    accepted BOOLEAN,
    accepted_at TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions (execution_id)
);
```

## Inspecting the Database

### Using Debug Endpoints

The following API endpoints are available for debugging:

1. List all executions:
```bash
curl http://localhost:8000/api/v1/llm/debug/executions
```

2. List all revisions:
```bash
curl http://localhost:8000/api/v1/llm/debug/revisions
```

3. Get specific execution details:
```bash
curl http://localhost:8000/api/v1/llm/debug/executions/{execution_id}
```

### Using CLI Tool

A command-line tool is available in `scripts/inspect_db.py` for inspecting the database:

1. View all tables:
```bash
python scripts/inspect_db.py
```

2. View specific tables:
```bash
# View executions table
python scripts/inspect_db.py --table executions

# View revisions table
python scripts/inspect_db.py --table revisions
```

3. View specific execution details:
```bash
python scripts/inspect_db.py --execution-id "your-execution-id"
```

## Status Values

### Execution Statuses
- `ACTIVE`: Successfully created execution plan
- `FAILED`: Error occurred during task generation
- `FATAL_ERROR`: Critical error during setup or epic retrieval

### Revision Statuses
- `PENDING`: Initial state when revision is requested
- `ACCEPTED`: User confirmed the interpretation
- `REJECTED`: User rejected the interpretation
- `APPLIED`: Changes have been applied to create new plan

## File Organization

The database-related files are organized as follows:
```
project_root/
├── data/
│   └── execution_tracker.db    # SQLite database file
├── scripts/
│   └── inspect_db.py          # CLI inspection tool
└── config/
    └── database.py            # Database configuration
```

## Development Notes

1. The database file is automatically created when the application starts
2. The database file is excluded from version control (listed in .gitignore)
3. The data directory is maintained in version control with a .gitkeep file

## Common Tasks

### Reset Database
To reset the database, simply delete the file:
```bash
rm data/execution_tracker.db
```
The application will create a new database file with the correct schema on next startup.

### Backup Database
To create a backup:
```bash
cp data/execution_tracker.db data/execution_tracker_backup_$(date +%Y%m%d_%H%M%S).db
```

### Database Location
The database location can be configured in `config/database.py`. The default location is:
```python
DATABASE = {
    "sqlite": {
        "path": str(PROJECT_ROOT / "data" / "execution_tracker.db")
    }
}
``` 