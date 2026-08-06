# Nimbus Backend

FastAPI and MongoDB persistence service for Nimbus projects, architecture versions,
chat history, and change requests. This service does not yet orchestrate the
Solution Architect Agent, generate Terraform, or implement authentication.

## Prerequisites

- Python 3.12 or newer
- A MongoDB Atlas cluster and connection string
- Network access from your machine to the Atlas cluster

In Atlas, add your current IP address to the project's network access list and
create a database user with access to the Nimbus database.

## Configure the environment

From `backend/`, copy the safe template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the Atlas connection string:

```dotenv
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
MONGODB_DB_NAME=nimbus_dev
```

Never commit `.env`. It is ignored by this service's `.gitignore`, while
`.env.example` remains tracked and contains no credentials. URL-encode special
characters in the MongoDB username or password.

## Install and run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

For Command Prompt, activate with `.venv\Scripts\activate.bat` instead.

Startup validates the MongoDB connection and creates the required indexes. It
fails with a clear message if `MONGODB_URI` is missing or Atlas is unreachable;
the connection string is never logged.

API documentation is available at <http://localhost:8000/docs>.

## Health checks

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/db
```

`/health` verifies the HTTP service. `/health/db` sends a MongoDB ping and returns
a safe `503` response when the database is unavailable.

## Create a mock project

This temporary endpoint persists a project, architecture version `1.0.0`, and
the initial user and assistant messages:

```powershell
$body = @{
  title = "Gaming Platform Dev Architecture"
  requirement = "I want to host a platform backend and multiple game backends on AWS."
  context = @{
    environment = "development"
    budgetPreference = "low"
    cloud = "AWS"
  }
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/projects/mock `
  -ContentType "application/json" `
  -Body $body
```

## Read and delete projects

```powershell
# List projects, newest updates first
Invoke-RestMethod http://localhost:8000/api/projects

# Load a complete workspace
Invoke-RestMethod http://localhost:8000/api/projects/<project-id>

# Read versions or messages
Invoke-RestMethod http://localhost:8000/api/projects/<project-id>/versions
Invoke-RestMethod http://localhost:8000/api/projects/<project-id>/messages

# Development-only cascading delete
Invoke-RestMethod -Method Delete http://localhost:8000/api/projects/<project-id>
```

## Tests

```powershell
python -m pytest
```

The API contract tests use injected fake services, so they do not need a live
MongoDB instance. Atlas integration can be tested separately by configuring a
dedicated test database in `.env`, starting the backend, and calling the mock
project endpoint. Do not point destructive integration tests at production data.

## Collections and indexes

The backend creates these collections lazily and ensures indexes at startup:

- `projects`: unique `slug`, `userId`, descending `createdAt`
- `architecture_versions`: `projectId`, unique `(projectId, version)`, and
  `(projectId, createdAt)`
- `chat_messages`: `(projectId, createdAt)`
- `change_requests`: `projectId`, `status`
