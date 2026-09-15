# Nimbus

Nimbus is an AI-assisted cloud infrastructure generation platform that turns natural-language infrastructure requirements into reviewable cloud architecture proposals and Terraform drafts.

The project is built around a human-in-the-loop workflow. Nimbus helps a developer, DevOps engineer, or cloud architect move from an idea to a structured Infrastructure-as-Code draft, but it does not blindly provision cloud resources. Users create a project from a requirement, review the generated architecture, approve or revise it, and only then generate Terraform files that can be validated and inspected before any deployment action happens outside the platform.

## What Nimbus Does

- Converts natural-language requirements into canonical cloud architecture JSON.
- Generates architecture reports, Mermaid diagrams, assumptions, risks, security notes, and cost considerations.
- Stores projects, architecture versions, messages, change requests, and Terraform generation history.
- Supports architecture review with accept, discard, redesign, and status workflows.
- Generates Terraform files from approved architecture versions.
- Uses deterministic Terraform renderers for trusted AWS patterns.
- Provides optional LLM-assisted reasoning, repair recommendations, and review layers.
- Validates generated Terraform with safe Terraform CLI commands when Terraform is installed.
- Keeps generated infrastructure artifacts reviewable before any real cloud deployment.

## Architecture

Nimbus is split into four main parts:

| Area | Path | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | React workspace for creating projects, reviewing architecture reports, viewing diagrams, approving versions, and downloading Terraform artifacts. |
| Backend API | `backend/` | FastAPI service that owns persistence, workspace APIs, project/version/message workflows, and HTTP calls to the agent services. |
| Solution Architect Agent | `agents/cloud-architect-agent/` | FastAPI agent that transforms natural-language requirements into validated canonical architecture JSON plus markdown and diagram output. |
| Terraform Generator Agent | `agents/terraform-generator-agent/` | FastAPI agent that converts approved architecture JSON into Terraform files, applies deterministic repairs, runs safety checks, and optionally validates with Terraform. |

Typical local ports:

| Service | Default URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Solution Architect Agent | `http://localhost:8001` |
| Terraform Generator Agent | `http://localhost:8002` |

## Generation Flow

1. A user enters an infrastructure requirement in the frontend.
2. The frontend calls the backend `POST /api/projects` endpoint.
3. The backend sends the requirement to the Solution Architect Agent.
4. The architect agent returns canonical architecture JSON, a rendered report, and diagram content.
5. The backend stores the project, initial architecture version, and messages in MongoDB.
6. The user reviews, edits, accepts, discards, or requests changes to architecture versions.
7. After approval, the backend calls the Terraform Generator Agent.
8. The generator returns Terraform files, derived resources, repairs, warnings, validation output, and next steps.

## Technology Stack

### Frontend

- React 19
- TypeScript
- Vite
- Tailwind CSS 4
- Radix UI component primitives
- Lucide React icons
- Wouter routing
- Mermaid diagrams
- React Markdown and syntax highlighting
- Framer Motion
- Zod

### Backend

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic and Pydantic Settings
- Motor and PyMongo
- MongoDB Atlas or a compatible MongoDB instance
- HTTPX for agent-to-agent calls
- Pytest and pytest-asyncio

### Agents

- Python 3.12+
- FastAPI
- Pydantic
- Jinja2 templates
- Provider abstraction for Gemini, Groq, OpenRouter, or deterministic-only operation
- Terraform CLI integration for safe validation

### Infrastructure Output

- Terraform
- AWS provider
- Current deterministic Terraform target: AWS VPC, public/private subnets, Internet Gateway, NAT Gateway, ALB, ECS Fargate, RDS PostgreSQL, Secrets Manager, IAM, and CloudWatch Logs.

## Repository Structure

```text
.
+-- backend/
|   +-- app/
|   |   +-- api/              # FastAPI routes
|   |   +-- core/             # config, database, errors
|   |   +-- models/           # persistence models
|   |   +-- repositories/     # MongoDB access layer
|   |   +-- schemas/          # API schemas
|   |   +-- services/         # project, version, agent, Terraform orchestration
|   +-- tests/
+-- agents/
|   +-- cloud-architect-agent/
|   |   +-- app/
|   |   |   +-- api/
|   |   |   +-- core/
|   |   |   +-- llm/
|   |   |   +-- prompts/
|   |   |   +-- renderers/
|   |   |   +-- schemas/
|   |   |   +-- services/
|   |   +-- tests/
|   +-- terraform-generator-agent/
|       +-- app/
|       |   +-- api/
|       |   +-- fallback/
|       |   +-- llm/
|       |   +-- planning/
|       |   +-- reasoning/
|       |   +-- renderers/
|       |   +-- rendering/
|       |   +-- review/
|       |   +-- safety/
|       |   +-- schemas/
|       |   +-- services/
|       |   +-- templates/
|       +-- tests/
+-- frontend/
    +-- client/
    |   +-- src/
    |       +-- components/
    |       +-- contexts/
    |       +-- data/
    |       +-- hooks/
    |       +-- pages/
    |       +-- services/
    |       +-- types/
    |       +-- utils/
    +-- server/
    +-- shared/
```

## Prerequisites

- Node.js with pnpm support for the frontend.
- Python 3.12 or newer for the backend and agents.
- MongoDB Atlas or another reachable MongoDB instance.
- Terraform installed and available on `PATH` if you want validation to run locally.
- Optional LLM API keys for Gemini, Groq, or OpenRouter.

## Environment Configuration

Create local `.env` files from the templates:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item agents\cloud-architect-agent\.env.example agents\cloud-architect-agent\.env
Copy-Item agents\terraform-generator-agent\.env.example agents\terraform-generator-agent\.env
```

Important backend settings:

```dotenv
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
MONGODB_DB_NAME=nimbus_dev
FRONTEND_URL=http://localhost:3000
SOLUTION_ARCHITECT_AGENT_URL=http://localhost:8001
TERRAFORM_GENERATOR_AGENT_URL=http://localhost:8002
```

Frontend API configuration is optional. By default the client calls `http://localhost:8000`.

```dotenv
VITE_NIMBUS_BACKEND_URL=http://localhost:8000
```

For deterministic Terraform generation, the Terraform agent can run with:

```dotenv
LLM_PROVIDER=none
```

For architecture generation, configure either Gemini or Groq in `agents/cloud-architect-agent/.env`.

## Local Development

Run each service in its own terminal.

### 1. Start the Solution Architect Agent

```powershell
cd agents\cloud-architect-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m uvicorn app.main:app --reload --port 8001
```

### 2. Start the Terraform Generator Agent

```powershell
cd agents\terraform-generator-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8002
```

### 3. Start the Backend API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Start the Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

## API Entry Points

Backend:

- `GET /health`
- `GET /health/db`
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/messages`
- `POST /api/projects/{project_id}/versions/{version_id}/accept`
- `POST /api/projects/{project_id}/versions/{version_id}/discard`
- `POST /api/projects/{project_id}/terraform/generate`
- `GET /api/projects/{project_id}/terraform/latest`

Solution Architect Agent:

- `GET /health`
- `POST /api/v1/architectures/analyze`

Terraform Generator Agent:

- `GET /health`
- `POST /api/v1/terraform/generate`
- `POST /api/v1/terraform/validate`
- `POST /api/v1/terraform/generate-and-validate`

Interactive API docs are available from each FastAPI service at `/docs`.

## Testing and Quality Checks

Backend tests:

```powershell
cd backend
python -m pytest
```

Cloud Architect Agent tests:

```powershell
cd agents\cloud-architect-agent
python -m pytest
```

Terraform Generator Agent tests:

```powershell
cd agents\terraform-generator-agent
python -m pytest
```

Frontend type check and production build:

```powershell
cd frontend
pnpm check
pnpm build
```

## Safety Model

Nimbus is designed to assist infrastructure authors, not replace review.

- It does not run `terraform apply` or `terraform destroy`.
- It does not generate AWS credentials or provider secrets.
- It stores database passwords through generated Terraform resources and Secrets Manager patterns.
- It warns about development-oriented defaults such as HTTP-only listeners, single NAT Gateway, or single-AZ database choices.
- It blocks unsafe Terraform validation commands and only runs controlled validation steps.
- It records missing inputs instead of inventing sensitive or deployment-specific values.
- Generated Terraform should always be reviewed before use in a real cloud account.

## Current Limitations

- AWS is the primary target cloud.
- The most complete deterministic Terraform path focuses on ECS Fargate, ALB, and PostgreSQL RDS.
- HTTPS, multi-NAT production networking, autoscaling, EKS, Lambda, DynamoDB, CloudFront, and multi-cloud generation are areas for future expansion.
- Authentication is not fully implemented in the backend.
- Terraform validation requires the Terraform CLI locally, and provider initialization may require network access.

## More Documentation

- Backend details: `backend/README.md`
- Solution Architect Agent details: `agents/cloud-architect-agent/README.md`
- Terraform Generator Agent details: `agents/terraform-generator-agent/README.md`
