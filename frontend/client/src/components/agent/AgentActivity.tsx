import AgentStep from "./AgentStep";

interface AgentActivityProps {
  isAnalyzing: boolean;
}

export default function AgentActivity({ isAnalyzing }: AgentActivityProps) {
  if (!isAnalyzing) {
    return null;
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
      <div className="mb-3">
        <p className="text-sm font-semibold text-foreground">Architect Agent Working</p>
        <p className="text-xs text-muted-foreground">
          Reviewing requirements, shaping the architecture, and preparing artifacts.
        </p>
      </div>
      <div className="space-y-3">
        <AgentStep
          status="completed"
          title="Requirement parsed"
          description="Business goal and constraints were extracted from the prompt."
        />
        <AgentStep
          status="active"
          title="Architecture reasoning"
          description="Evaluating infrastructure tradeoffs and preparing reviewable outputs."
        />
        <AgentStep
          status="pending"
          title="Artifact refresh"
          description="Updating diagrams, report, and canonical JSON."
        />
      </div>
    </div>
  );
}
