# Cloud Architect Agent Service

This service is part of an intelligent platform that automates Cloud infrastructure design and Infrastructure as Code (IaC) generation. The **Solution Architect Agent** acts as a senior AWS architect, transforming natural language requirements into a validated **Canonical Architecture JSON**.

## Global Vision
1. **Solution Architect Agent** (This service): Designs architecture and outputs JSON.
2. **IaC Generator Agent**: Consumes JSON and produces Terraform/Kubernetes code.
3. **Validator Agent**: Audits code for security and best practices.

## Key Features
- **Deterministic Rendering**: Markdown reports and Mermaid diagrams are generated from the JSON source of truth.
- **Strict Validation**: Pydantic schemas ensure the architecture is consistent and deployable.
- **Provider Abstraction**: Supports Google Gemini and Groq.

## Installation

### Prerequisites
- Python 3.12+
- Gemini or Groq API Key

### Setup
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install .
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Usage

### Starting the API
```bash
uvicorn app.main:app --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) for the Swagger UI.

### API Endpoints
- `GET /health`: Health check.
- `POST /api/v1/architectures/analyze`: Submit a requirement for analysis.

### Example Request
```json
{
  "requirement": "Deploy a small containerized web application with PostgreSQL. This is a development environment and the budget should remain low.",
  "context": {
    "environment": "development"
  }
}
```

## Testing
Run unit and API tests:
```bash
pytest
```

Run live smoke tests:
```bash
python scripts/smoke_test.py --provider gemini
```

## Supported AWS Resources
- VPC, Subnets, IGW, NAT Gateway
- EC2, ECS Fargate, ALB
- S3, RDS PostgreSQL
- IAM Role, Secrets Manager, CloudWatch
