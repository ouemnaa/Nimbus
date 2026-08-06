export type ArchitectureStatus =
  | "READY_FOR_REVIEW"
  | "DRAFT_REVISION"
  | "APPROVED"
  | "NEEDS_CLARIFICATION"
  | "UNSUPPORTED";
export type Environment = "development" | "staging" | "production";
export type BudgetPreference = "MINIMIZE_COST" | "BALANCED" | "PERFORMANCE_FIRST";
export type AvailabilityRequirement = "STANDARD" | "HIGH" | "CRITICAL";
export type CloudProvider = "AWS";

export interface RequirementContext {
  environment: Environment;
  budget_preference: string;
  cloud: CloudProvider;
  region?: string;
}

export interface ArchitectureComponent {
  id: string;
  name: string;
  type?: string;
  provider_type?: string;
  category: string;
  purpose: string;
  scope: string;
  configuration?: Record<string, unknown>;
  dependencies?: string[];
  depends_on?: string[];
  diagram_visibility?: string;
}

export interface ArchitectureDecision {
  id?: string;
  title: string;
  decision?: string;
  rationale: string;
  alternatives?: Array<{
    name: string;
    pros: string[];
    cons: string[];
    reason_not_selected: string;
  }>;
  alternatives_considered?: Array<{
    option: string;
    advantages: string[];
    disadvantages: string[];
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
  architecture_version: number | string;
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
    budget_preference?: string;
    availability_requirement?: string;
  };
  cloud: {
    provider: CloudProvider;
    region: string;
    region_rationale: string;
  };
  solution: string | {
    summary: string;
    architecture_pattern: string;
  };
  resources: ArchitectureComponent[];
  relationships: Array<{
    source?: string;
    target?: string;
    type?: string;
    source_id?: string;
    target_id?: string;
    relationship_type?: string;
    label?: string;
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
    risk?: string;
    title?: string;
    description?: string;
    severity?: string;
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
  architecture: CanonicalArchitecture;
  report_markdown: string;
  metadata: {
    provider: string;
    model: string;
    generation_duration_ms: number;
  };
}

export interface BackendProject {
  id: string;
  title: string;
  slug: string;
  initialRequirement: string;
  context: Record<string, unknown>;
  currentVersionId: string | null;
  status: ArchitectureStatus;
  userId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BackendArchitectureVersion {
  id: string;
  projectId: string;
  version: string;
  parentVersionId: string | null;
  status: ArchitectureStatus;
  architecture: CanonicalArchitecture;
  reportMarkdown: string;
  simpleDiagramMermaid: string | null;
  advancedDiagramMermaid: string | null;
  changeSummary: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface BackendChatMessage {
  id: string;
  projectId: string;
  architectureVersionId: string | null;
  role: "user" | "assistant" | "system";
  content: string;
  intent: "INITIAL" | "EXPLAIN" | "MODIFY" | "CLARIFY" | "UNSUPPORTED" | "SYSTEM";
  architectureChanged: boolean;
  createdAt: string;
}

export interface BackendChangeRequest {
  id: string;
  projectId: string;
  fromVersionId: string;
  toVersionId: string | null;
  userMessage: string;
  changeSummary: string[];
  status: "pending" | "accepted" | "discarded";
  createdAt: string;
  updatedAt: string;
}

export interface ProjectWorkspaceResponse {
  project: BackendProject;
  currentVersion: BackendArchitectureVersion | null;
  versions: BackendArchitectureVersion[];
  messages: BackendChatMessage[];
}

export interface ProjectMessageResponse {
  intent: "EXPLAIN" | "MODIFY" | "CLARIFY" | "UNSUPPORTED";
  architectureChanged: boolean;
  answer: string;
  messages: BackendChatMessage[];
  project?: BackendProject | null;
  currentVersion?: BackendArchitectureVersion | null;
  draftVersion?: BackendArchitectureVersion | null;
  changeRequest?: BackendChangeRequest | null;
  changeSummary: string[];
}
