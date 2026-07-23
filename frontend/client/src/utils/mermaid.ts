export function generateHighLevelDiagram(title: string): string {
  return `flowchart LR
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
    ecs --> cloudwatch`;
}

export function generateNetworkDiagram(region: string): string {
  return `flowchart TB
    internet["Internet"]

    subgraph aws["AWS Region: ${region}"]

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
    ecs --> rds`;
}

