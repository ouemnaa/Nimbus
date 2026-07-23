import { CanonicalArchitecture } from "@/types/architecture";

export const mockArchitecture: CanonicalArchitecture = {
  schema_version: "1.0",
  architecture_id: "arch-demo-001",
  architecture_version: 1,
  status: "READY_FOR_REVIEW",
  title: "Low-Cost Containerized Web Application",
  requirement_summary: {
    business_goal: "Deploy a public containerized application with persistent PostgreSQL storage.",
    application_type: "Containerized web application",
    environment: "development",
    expected_users_or_traffic: "Low initial traffic",
    functional_requirements: [
      "Public application access",
      "Persistent relational database"
    ],
    non_functional_requirements: [
      "Low operational overhead",
      "Secure database access",
      "Ability to scale later"
    ],
    constraints: [
      "AWS cloud",
      "Low-cost development environment"
    ],
    budget_preference: "MINIMIZE_COST",
    availability_requirement: "STANDARD"
  },
  cloud: {
    provider: "AWS",
    region: "eu-west-1",
    region_rationale: "Selected as a representative European AWS region with good availability and cost profile."
  },
  solution: {
    summary: "Run the containerized application on ECS Fargate behind an Application Load Balancer and store application data in a private RDS PostgreSQL database.",
    architecture_pattern: "Managed containerized web application"
  },
  resources: [
    {
      id: "vpc-001",
      name: "Application VPC",
      type: "AWS VPC",
      category: "Networking",
      purpose: "Provides isolated networking for application resources.",
      scope: "private",
      configuration: {
        cidr: "10.0.0.0/16"
      }
    },
    {
      id: "alb-001",
      name: "Application Load Balancer",
      type: "AWS Application Load Balancer",
      category: "Load balancing",
      purpose: "Receives public HTTP/HTTPS traffic and routes it to the application service.",
      scope: "public",
      dependencies: ["vpc-001"]
    },
    {
      id: "ecs-001",
      name: "ECS Fargate Service",
      type: "AWS ECS Fargate",
      category: "Compute",
      purpose: "Runs containerized application workloads without managing EC2 instances.",
      scope: "private",
      configuration: {
        cpu: "256",
        memory: "512",
        desiredCount: 2
      },
      dependencies: ["vpc-001", "alb-001"]
    },
    {
      id: "rds-001",
      name: "RDS PostgreSQL",
      type: "AWS RDS PostgreSQL",
      category: "Database",
      purpose: "Provides managed persistent relational storage inside private subnets.",
      scope: "private",
      configuration: {
        engine: "postgres",
        version: "15.3",
        instanceClass: "db.t3.micro",
        allocatedStorage: "20"
      },
      dependencies: ["vpc-001"]
    },
    {
      id: "secrets-001",
      name: "AWS Secrets Manager",
      type: "AWS Secrets Manager",
      category: "Security",
      purpose: "Stores database credentials outside application configuration.",
      scope: "private",
      dependencies: ["ecs-001", "rds-001"]
    },
    {
      id: "cloudwatch-001",
      name: "Amazon CloudWatch",
      type: "AWS CloudWatch",
      category: "Observability",
      purpose: "Collects application logs and operational metrics.",
      scope: "private",
      dependencies: ["ecs-001", "rds-001"]
    }
  ],
  relationships: [
    { source: "internet", target: "alb-001", type: "traffic" },
    { source: "alb-001", target: "ecs-001", type: "routes" },
    { source: "ecs-001", target: "rds-001", type: "queries" },
    { source: "ecs-001", target: "secrets-001", type: "retrieves" },
    { source: "ecs-001", target: "cloudwatch-001", type: "logs" }
  ],
  decisions: [
    {
      id: "dec-001",
      title: "Use ECS Fargate",
      rationale: "The workload is containerized and prioritizes low operational overhead. Fargate eliminates server management while providing reliable container orchestration.",
      alternatives: [
        {
          name: "EC2",
          pros: ["Maximum configuration control", "Potentially lower cost at scale"],
          cons: ["Requires server maintenance and capacity management", "Higher operational complexity"],
          reason_not_selected: "Adds operational work that is unnecessary for the stated requirement."
        },
        {
          name: "EKS",
          pros: ["Advanced Kubernetes orchestration", "Multi-cluster support"],
          cons: ["Greater cost and operational complexity", "Overkill for simple containerized apps"],
          reason_not_selected: "The workload does not currently justify Kubernetes complexity."
        }
      ]
    },
    {
      id: "dec-002",
      title: "Private RDS PostgreSQL",
      rationale: "Managed database service eliminates operational overhead while providing security through private subnet placement and Secrets Manager integration.",
      alternatives: [
        {
          name: "Self-managed PostgreSQL on EC2",
          pros: ["Full control", "Potentially lower cost"],
          cons: ["Requires backup, patching, and monitoring", "Higher operational burden"],
          reason_not_selected: "Contradicts the low-operational-overhead requirement."
        },
        {
          name: "Aurora PostgreSQL",
          pros: ["Advanced features", "Better scalability"],
          cons: ["Higher cost", "Unnecessary for development environment"],
          reason_not_selected: "Overkill for low-cost development requirement."
        }
      ]
    }
  ],
  security_considerations: [
    "Application Load Balancer terminates public traffic; application runs in private subnets.",
    "Database credentials stored in AWS Secrets Manager, not in application code or environment variables.",
    "Network isolation via VPC security groups restricts database access to ECS tasks only.",
    "CloudWatch logs encrypted at rest and accessible only to authorized users."
  ],
  reliability_considerations: [
    "ECS Fargate with desired count of 2 provides basic redundancy across availability zones.",
    "Application Load Balancer automatically routes traffic away from unhealthy targets.",
    "RDS automated backups enabled; point-in-time recovery available.",
    "CloudWatch alarms can notify on application or database failures."
  ],
  scalability_considerations: [
    "ECS service can scale horizontally by increasing desired task count.",
    "Application Load Balancer distributes traffic across multiple tasks.",
    "RDS can be scaled vertically (instance class upgrade) or horizontally (read replicas) if needed.",
    "Architecture supports future migration to Aurora or multi-region setup."
  ],
  cost_considerations: [
    "ECS Fargate pricing is per-task-hour; on-demand pricing suitable for development.",
    "RDS db.t3.micro is cost-effective for low-traffic development workloads.",
    "Application Load Balancer incurs hourly charge plus data processing fees.",
    "Estimated monthly cost: ~$50-80 for development environment."
  ],
  operational_considerations: [
    "ECS Fargate abstracts infrastructure management; focus on container image updates.",
    "RDS automated backups and patching reduce operational toil.",
    "CloudWatch provides centralized logging; set up alarms for critical metrics.",
    "Consider implementing infrastructure-as-code (Terraform) for reproducibility."
  ],
  assumptions: [
    "Application is containerized and available as a Docker image.",
    "Database schema is compatible with PostgreSQL 15.3.",
    "Expected traffic is low enough for single-AZ RDS instance.",
    "Development environment can tolerate brief downtime during updates.",
    "Team has basic AWS knowledge and access to AWS console."
  ],
  open_questions: [
    "What is the expected database size and growth rate?",
    "Are there specific compliance or data residency requirements?",
    "Should the application support multiple environments (dev, staging, prod)?",
    "Is disaster recovery (multi-region) a future requirement?"
  ],
  risks: [
    {
      risk: "Single-AZ RDS instance is a single point of failure.",
      mitigation: "Upgrade to Multi-AZ RDS deployment for production environments."
    },
    {
      risk: "Application Load Balancer is a fixed cost even with low traffic.",
      mitigation: "For very low traffic, consider API Gateway + Lambda as alternative."
    },
    {
      risk: "No built-in disaster recovery or backup strategy.",
      mitigation: "Implement automated backups, cross-region replication, and recovery procedures."
    }
  ],
  limitations: [
    "Single-AZ deployment limits availability.",
    "No built-in caching layer (ElastiCache); consider adding for performance.",
    "No CDN for static assets; consider CloudFront for global distribution.",
    "Monitoring limited to CloudWatch; consider third-party observability tools for production."
  ],
  recommended_diagrams: ["HIGH_LEVEL", "NETWORK"],
  high_level_diagram: `flowchart LR
    internet["Internet"]
    alb["Application Load Balancer"]
    ecs["ECS Fargate Service"]
    rds[("RDS PostgreSQL")]
    secrets["AWS Secrets Manager"]
    cloudwatch["Amazon CloudWatch"]

    internet --> alb
    alb --> ecs
    ecs --> rds
    ecs --> secrets
    ecs --> cloudwatch`,
  network_diagram: `flowchart TB
    internet["Internet"]

    subgraph aws["AWS Region: eu-west-1"]

        subgraph vpc["Application VPC"]

            subgraph public["Public Subnets"]
                alb["Application Load Balancer"]
            end

            subgraph private_app["Private Application Subnets"]
                ecs["ECS Fargate Tasks"]
            end

            subgraph private_data["Private Data Subnets"]
                rds[("RDS PostgreSQL")]
            end

        end
    end

    internet --> alb
    alb --> ecs
    ecs --> rds`,
  markdown_report: `# Proposed Cloud Architecture

## Requirement Understanding

Deploy a low-cost containerized web application on AWS with PostgreSQL. The application should be publicly accessible, but the database must remain private.

## Recommended Solution

A cost-conscious containerized web architecture using Amazon ECS Fargate behind an Application Load Balancer, with PostgreSQL hosted privately on Amazon RDS.

## High-Level Architecture

\`\`\`mermaid
flowchart LR
    internet["Internet"]
    alb["Application Load Balancer"]
    ecs["ECS Fargate Service"]
    rds[("RDS PostgreSQL")]
    secrets["AWS Secrets Manager"]
    cloudwatch["Amazon CloudWatch"]

    internet --> alb
    alb --> ecs
    ecs --> rds
    ecs --> secrets
    ecs --> cloudwatch
\`\`\`

## Network Architecture

\`\`\`mermaid
flowchart TB
    internet["Internet"]

    subgraph aws["AWS Region: eu-west-1"]

        subgraph vpc["Application VPC"]

            subgraph public["Public Subnets"]
                alb["Application Load Balancer"]
            end

            subgraph private_app["Private Application Subnets"]
                ecs["ECS Fargate Tasks"]
            end

            subgraph private_data["Private Data Subnets"]
                rds[("RDS PostgreSQL")]
            end

        end
    end

    internet --> alb
    alb --> ecs
    ecs --> rds
\`\`\`

## Architecture Components

### Networking

**Application VPC** - Provides isolated networking for application resources.

### Compute

**ECS Fargate Service** - Runs containerized application workloads without managing EC2 instances.

### Load Balancing

**Application Load Balancer** - Receives public HTTP/HTTPS traffic and routes it to the application service.

### Database

**RDS PostgreSQL** - Provides managed persistent relational storage inside private subnets.

### Security

**AWS Secrets Manager** - Stores database credentials outside application configuration.

### Observability

**Amazon CloudWatch** - Collects application logs and operational metrics.

## Architecture Decisions

### Use ECS Fargate

**Rationale:** The workload is containerized and prioritizes low operational overhead. Fargate eliminates server management while providing reliable container orchestration.

**Alternatives Considered:**

- **EC2**: Requires server maintenance and capacity management. Adds operational work unnecessary for the stated requirement.
- **EKS**: Kubernetes orchestration is overkill for simple containerized apps. Greater cost and operational complexity.

### Private RDS PostgreSQL

**Rationale:** Managed database service eliminates operational overhead while providing security through private subnet placement and Secrets Manager integration.

**Alternatives Considered:**

- **Self-managed PostgreSQL on EC2**: Requires backup, patching, and monitoring. Contradicts the low-operational-overhead requirement.
- **Aurora PostgreSQL**: Better scalability but higher cost and unnecessary for development environment.

## Security Considerations

- Application Load Balancer terminates public traffic; application runs in private subnets.
- Database credentials stored in AWS Secrets Manager, not in application code or environment variables.
- Network isolation via VPC security groups restricts database access to ECS tasks only.
- CloudWatch logs encrypted at rest and accessible only to authorized users.

## Reliability and Scalability

- ECS Fargate with desired count of 2 provides basic redundancy across availability zones.
- Application Load Balancer automatically routes traffic away from unhealthy targets.
- RDS automated backups enabled; point-in-time recovery available.
- ECS service can scale horizontally by increasing desired task count.
- RDS can be scaled vertically (instance class upgrade) or horizontally (read replicas) if needed.

## Cost Considerations

- ECS Fargate pricing is per-task-hour; on-demand pricing suitable for development.
- RDS db.t3.micro is cost-effective for low-traffic development workloads.
- Application Load Balancer incurs hourly charge plus data processing fees.
- Estimated monthly cost: ~$50-80 for development environment.

## Operational Considerations

- ECS Fargate abstracts infrastructure management; focus on container image updates.
- RDS automated backups and patching reduce operational toil.
- CloudWatch provides centralized logging; set up alarms for critical metrics.
- Consider implementing infrastructure-as-code (Terraform) for reproducibility.

## Assumptions

- Application is containerized and available as a Docker image.
- Database schema is compatible with PostgreSQL 15.3.
- Expected traffic is low enough for single-AZ RDS instance.
- Development environment can tolerate brief downtime during updates.
- Team has basic AWS knowledge and access to AWS console.

## Open Questions

- What is the expected database size and growth rate?
- Are there specific compliance or data residency requirements?
- Should the application support multiple environments (dev, staging, prod)?
- Is disaster recovery (multi-region) a future requirement?

## Risks and Mitigations

- **Single-AZ RDS instance is a single point of failure** → Upgrade to Multi-AZ RDS deployment for production environments.
- **Application Load Balancer is a fixed cost even with low traffic** → For very low traffic, consider API Gateway + Lambda as alternative.
- **No built-in disaster recovery or backup strategy** → Implement automated backups, cross-region replication, and recovery procedures.

## Known Limitations

- Single-AZ deployment limits availability.
- No built-in caching layer (ElastiCache); consider adding for performance.
- No CDN for static assets; consider CloudFront for global distribution.
- Monitoring limited to CloudWatch; consider third-party observability tools for production.

## Review Status

This architecture is ready for human review and approval.
`
};

export const mockProjects = [
  {
    id: "demo-architecture",
    title: "Low-Cost Containerized Web Application",
    requirement: "Design AWS infrastructure for a small containerized web application with PostgreSQL. This is a development environment and cost should remain low.",
    status: "READY_FOR_REVIEW" as const,
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    resourceCount: 6,
    context: {
      environment: "development" as const,
      budgetPreference: "MINIMIZE_COST" as const,
      cloud: "AWS" as const,
      region: "eu-west-1",
    },
    architecture: mockArchitecture,
  },
  {
    id: "static-website",
    title: "Global Static Website",
    requirement: "Host a globally available static website with HTTPS and low operational overhead.",
    status: "APPROVED" as const,
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    resourceCount: 3,
    context: {
      environment: "production" as const,
      budgetPreference: "BALANCED" as const,
      cloud: "AWS" as const,
      region: "us-east-1",
    },
    architecture: mockArchitecture,
  },
  {
    id: "production-api",
    title: "Production Analytics API",
    requirement: "Design a highly available public API with private PostgreSQL storage, secure secret management and monitoring.",
    status: "NEEDS_CLARIFICATION" as const,
    createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    resourceCount: 8,
    context: {
      environment: "production" as const,
      budgetPreference: "PERFORMANCE_FIRST" as const,
      cloud: "AWS" as const,
      region: "eu-central-1",
    },
    architecture: mockArchitecture,
  },
];
