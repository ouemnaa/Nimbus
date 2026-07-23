import { Card } from "@/components/ui/card";
import { CanonicalArchitecture } from "@/types/architecture";

interface ArchitectureOverviewProps {
  architecture: CanonicalArchitecture;
}

export default function ArchitectureOverview({ architecture }: ArchitectureOverviewProps) {
  const solutionSummary =
    typeof architecture.solution === "string"
      ? architecture.solution
      : architecture.solution.summary;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Architecture Summary</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {solutionSummary || "No solution summary was returned."}
        </p>
      </Card>

      {/* Architecture Qualities */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-4">Architecture Qualities</h3>
        <ul className="space-y-2">
          {[
            "Managed compute",
            "Private database",
            "Low operational overhead",
            "Secure secret handling",
          ].map((quality) => (
            <li key={quality} className="text-sm text-muted-foreground flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-primary rounded-full" />
              {quality}
            </li>
          ))}
        </ul>
      </Card>

      {/* Architecture Assessment */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-4">Architecture Assessment</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Security", value: "Strong" },
            { label: "Cost Efficiency", value: "High" },
            { label: "Operational Complexity", value: "Low–Medium" },
            { label: "Scalability", value: "Good" },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-medium text-foreground mt-1">{value}</p>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6 bg-background border-border">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Security Considerations
          </h3>
          {architecture.security_considerations.length ? (
            <ul className="space-y-2">
              {architecture.security_considerations.map((item, index) => (
                <li key={index} className="text-sm text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No security considerations were returned.
            </p>
          )}
        </Card>

        <Card className="p-6 bg-background border-border">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Cost Considerations
          </h3>
          {architecture.cost_considerations.length ? (
            <ul className="space-y-2">
              {architecture.cost_considerations.map((item, index) => (
                <li key={index} className="text-sm text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No cost considerations were returned.
            </p>
          )}
        </Card>
      </div>

      {/* Assumptions */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Assumptions</h3>
        <ul className="space-y-2">
          {architecture.assumptions.map((assumption, idx) => (
            <li key={idx} className="text-sm text-muted-foreground">
              • {assumption}
            </li>
          ))}
        </ul>
      </Card>

      {/* Open Questions */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Open Questions</h3>
        <ul className="space-y-2">
          {architecture.open_questions.map((question, idx) => (
            <li key={idx} className="text-sm text-muted-foreground">
              • {question}
            </li>
          ))}
        </ul>
      </Card>

      {/* Risks */}
      <Card className="p-6 bg-background border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Risks & Mitigations</h3>
        <div className="space-y-3">
          {architecture.risks.map((risk, idx) => (
            <div key={idx}>
              <p className="text-sm font-medium text-foreground">
                {risk.title || risk.risk || "Architecture risk"}
              </p>
              {risk.description && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {risk.description}
                </p>
              )}
              <p className="text-sm text-muted-foreground mt-1">→ {risk.mitigation}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
