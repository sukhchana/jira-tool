# JIRA Ticket Creator with LLM Support

A FastAPI application that leverages Google's Vertex AI (Gemini) to help create, analyze, and break down JIRA tickets and epics.

## Architecture

The application follows a modular, service-oriented architecture:

### Core Components

1. **LLM Module** (`llm/`)
   - `vertexllm.py`: Handles communication with Google's Vertex AI service
   - Provides a clean interface for LLM operations

2. **Services** (`services/`)
   - `jira_service.py`: Handles JIRA API interactions
   - `jira_breakdown_service.py`: Orchestrates epic breakdown and ticket creation
   - `prompt_helper_service.py`: Manages LLM prompt templates
   - `ticket_parser_service.py`: Parses LLM responses into structured data

3. **Routers** (`routers/`)
   - `jira_router.py`: JIRA-related endpoints
   - `llm_router.py`: LLM-related endpoints

4. **Utils** (`utils/`)
   - `logger.py`: Centralized logging configuration

### Architecture Flow
┌─────────────────┐
│ │
│ Client Request │
│ │
└────────┬────────┘
│
▼
┌─────────────────┐
│ FastAPI Router │
└────────┬────────┘
│
▼
┌───────────────────────────┐
│ JiraBreakdownService │
└──┬────────────┬────────┬──┘
│ │ │
┌──────────────┘ │ └──────────────┐
▼ ▼ ▼
┌────────────────────┐ ┌────────────────────┐ ┌─────────────────────┐
│ VertexLLM │ │ PromptHelper │ │ TicketParser │
│ │ │ │ │ │
└─────────┬──────────┘ └────────┬──────────┘ └──────────┬──────────┘
│ │ │
▼ │ │
┌────────────────────┐ │ │
│ Vertex AI API │ │ │
└────────┬──────────┘ │ │
│ │ │
└───────────────────────────┼──────────────────────────┘
│
▼
┌────────────────────┐
│ JIRA Service │
└────────┬───────────┘
│
▼
┌────────────────────┐
│ JIRA API │
└────────────────────┘

## Setup

### Prerequisites

- Python 3.8+
- Google Cloud account with Vertex AI enabled
- JIRA account with API access
- Git

### Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd jira-ticket-creator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```env
# JIRA Settings
JIRA_API_TOKEN=your_base64_encoded_token
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@example.com

# Google Cloud Settings
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

### Google Cloud Setup

1. Create a Google Cloud project
2. Enable Vertex AI API
3. Create a service account and download the key file
4. Set the path to your service account key in the `.env` file

### JIRA Setup

1. Generate an API token from your Atlassian account
2. Base64 encode your email:token combination
3. Add the encoded credentials to your `.env` file

## Running the Application

1. Start the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

2. Access the API documentation:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### JIRA LLM Operations

- `POST /api/v1/llm/generate-description/`
  - Generate a structured JIRA ticket description
  - Request body: `TicketGenerationRequest`
  - Response: `TicketGenerationResponse`

- `POST /api/v1/llm/analyze-complexity/`
  - Analyze ticket complexity and estimate story points
  - Request body: `ComplexityAnalysisRequest`
  - Response: `ComplexityAnalysisResponse`

- `POST /api/v1/llm/break-down-epic/{epic_key}`
  - Break down a JIRA epic into smaller tasks
  - Path parameter: `epic_key`
  - Response: `EpicBreakdownResponse`

- `POST /api/v1/llm/create-epic-subtasks/{epic_key}`
  - Break down an epic and optionally create subtasks in JIRA
  - Path parameter: `epic_key`
  - Query parameter: `create_in_jira` (boolean)
  - Response: `EpicBreakdownResponse`

## Revision Flow

The application supports a structured workflow for revising execution plans:

### 1. Request Revision
**Endpoint:** `POST /revise-plan/`
- User submits revision request with:
  - `execution_id`: Original execution plan ID
  - `revision_request`: Free-text description of desired changes
- System uses LLM to interpret and structure the request
- Returns a `temp_revision_id` and interpreted changes for confirmation

### 2. Confirm Interpretation
**Endpoint:** `POST /confirm-revision-request/{temp_revision_id}`
- User reviews the LLM's interpretation
- Accepts or rejects the interpretation
- System tracks the decision in SQLite database
- Status updated to ACCEPTED/REJECTED

### 3. Apply Changes
**Endpoint:** `POST /apply-revision/{temp_revision_id}`
- Only proceeds if revision was accepted
- Generates new execution plan with changes
- Creates new files with updated content
- Links new execution to original via parent relationship

### Database Structure

The system uses SQLite to track executions and revisions:

```sql
-- Track execution plans
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

-- Track revision requests and their status
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

### File Organization

The system maintains several types of files:
- **Execution Plans**: `execution_plans/EXECUTION_{epic_key}_{timestamp}.md`
  - Contains the detailed execution plan
  - Linked to parent plan for revision tracking

- **Proposed Tickets**: `proposed_tickets/PROPOSED_{epic_key}_{timestamp}.yaml`
  - Contains structured ticket definitions
  - Maintains consistency with execution plan

- **Database**: `data/execution_tracker.db`
  - SQLite database tracking all relationships
  - Stores execution and revision history

### Revision States

A revision can be in one of these states:
- `PENDING`: Initial state when revision is requested
- `ACCEPTED`: User confirmed the interpretation
- `REJECTED`: User rejected the interpretation
- `APPLIED`: Changes have been applied to create new plan

### Example Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LLM
    participant DB
    participant Files

    User->>API: POST /revise-plan/
    API->>LLM: Interpret revision request
    LLM-->>API: Structured interpretation
    API->>DB: Store revision (PENDING)
    API-->>User: Return temp_revision_id

    User->>API: POST /confirm-revision-request/
    API->>DB: Update status (ACCEPTED/REJECTED)
    API-->>User: Confirmation response

    User->>API: POST /apply-revision/
    API->>DB: Check acceptance
    API->>Files: Generate new plans
    API->>DB: Create new execution record
    API-->>User: Return new execution details
```

## Logging

The application uses Loguru for logging:
- Console output: INFO level and above
- File output: DEBUG level and above (in `logs/app.log`)
- Log rotation: 500MB file size
- Log retention: 10 days

## Development

### Project Structure
```
├── llm/
│   ├── __init__.py
│   └── vertexllm.py
├── services/
│   ├── __init__.py
│   ├── jira_service.py
│   ├── jira_breakdown_service.py
│   ├── prompt_helper_service.py
│   └── ticket_parser_service.py
├── routers/
│   ├── __init__.py
│   ├── jira_router.py
│   └── llm_router.py
├── utils/
│   ├── __init__.py
│   └── logger.py
├── main.py
├── requirements.txt
└── .env
```

### Adding New Features

1. Add new service classes in the `services/` directory
2. Create new routers in the `routers/` directory
3. Update the OpenAPI documentation in the router decorators
4. Add appropriate logging
5. Update type hints and response models

## Error Handling

The application includes comprehensive error handling:
- HTTP exceptions with detailed error messages
- Logging of all errors with stack traces
- Structured error responses

## Security Considerations

1. In production:
   - Replace `allow_origins=["*"]` with specific origins
   - Secure the API with authentication
   - Use proper HTTPS certificates
   - Restrict JIRA API permissions
   - Implement rate limiting

2. Environment variables:
   - Never commit `.env` file
   - Rotate API keys regularly
   - Use secret management in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

