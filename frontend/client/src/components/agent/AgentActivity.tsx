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
        <p className="text-sm font-semibold text-foreground">
          Sending requirement to Solution Architect
        </p>
        <p className="text-xs text-muted-foreground">
          The agent is analyzing your request and preparing the reviewable artifact.
        </p>
      </div>
      <div className="space-y-3">
        <AgentStep
          status="completed"
          title="Analyzing architecture needs"
          description="Reviewing the business goal, constraints, and environment."
        />
        <AgentStep
          status="active"
          title="Generating cloud architecture"
          description="Evaluating infrastructure choices and their tradeoffs."
        />
        <AgentStep
          status="pending"
          title="Preparing reviewable artifact"
          description="Building the report and canonical architecture JSON."
        />
      </div>
    </div>
  );
}
