export type ArchitectureStatus = "READY_FOR_REVIEW" | "APPROVED" | "NEEDS_CLARIFICATION";
export type Environment = "development" | "staging" | "production";
export type BudgetPreference = "MINIMIZE_COST" | "BALANCED" | "PERFORMANCE_FIRST";
export type AvailabilityRequirement = "STANDARD" | "HIGH" | "CRITICAL";
export type CloudProvider = "AWS";

export interface RequirementContext {
  environment: Environment;
  budgetPreference: BudgetPreference;
  cloud: CloudProvider;
  region: string;
}

export interface ArchitectureComponent {
  id: string;
  name: string;
  type: string;
  category: string;
  purpose: string;
  scope: "public" | "private";
  configuration?: Record<string, unknown>;
  dependencies?: string[];
}

export interface ArchitectureDecision {
  id: string;
  title: string;
  rationale: string;
  alternatives: Array<{
    name: string;
    pros: string[];
    cons: string[];
    reason_not_selected: string;
  }>;
}

export interface ArchitectureScore {
  security: string;
  costEfficiency: string;
  operationalComplexity: string;
  scalability: string;
}

export interface CanonicalArchitecture {
  schema_version: string;
  architecture_id: string;
  architecture_version: number;
  status: ArchitectureStatus;
  title: string;
  requirement_summary: {
    business_goal: string;
    application_type: string;
    environment: Environment;
    expected_users_or_traffic: string;
    functional_requirements: string[];
    non_functional_requirements: string[];
    constraints: string[];
    budget_preference: BudgetPreference;
    availability_requirement: AvailabilityRequirement;
  };
  cloud: {
    provider: CloudProvider;
    region: string;
    region_rationale: string;
  };
  solution: {
    summary: string;
    architecture_pattern: string;
  };
  resources: ArchitectureComponent[];
  relationships: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  decisions: ArchitectureDecision[];
  security_considerations: string[];
  reliability_considerations: string[];
  scalability_considerations: string[];
  cost_considerations: string[];
  operational_considerations: string[];
  assumptions: string[];
  open_questions: string[];
  risks: Array<{
    risk: string;
    mitigation: string;
  }>;
  limitations: string[];
  recommended_diagrams: string[];
  markdown_report?: string;
  high_level_diagram?: string;
  network_diagram?: string;
}

export interface Project {
  id: string;
  title: string;
  requirement: string;
  context: RequirementContext;
  architecture: CanonicalArchitecture;
  status: ArchitectureStatus;
  createdAt: Date;
  updatedAt: Date;
  resourceCount: number;
}

export interface AnalyzeArchitectureRequest {
  requirement: string;
  context: RequirementContext;
}

export interface AnalyzeArchitectureResponse {
  projectId: string;
  architecture: CanonicalArchitecture;
}

