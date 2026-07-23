import { useState } from "react";
import { Card } from "@/components/ui/card";
import { ArchitectureDecision } from "@/types/architecture";
import { ChevronDown } from "lucide-react";

interface ArchitectureDecisionsProps {
  decisions: ArchitectureDecision[];
}

export default function ArchitectureDecisions({ decisions }: ArchitectureDecisionsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      {decisions.map((decision) => (
        <Card
          key={decision.id}
          className="bg-background border-border overflow-hidden"
        >
          <button
            onClick={() =>
              setExpandedId(expandedId === decision.id ? null : decision.id)
            }
            className="w-full p-4 flex items-center justify-between hover:bg-accent/5 transition-colors"
          >
            <h3 className="font-medium text-sm text-foreground text-left">
              {decision.title}
            </h3>
            <ChevronDown
              className={`w-4 h-4 text-muted-foreground transition-transform ${
                expandedId === decision.id ? "rotate-180" : ""
              }`}
            />
          </button>

          {expandedId === decision.id && (
            <div className="px-4 pb-4 border-t border-border pt-4 space-y-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Rationale
                </p>
                <p className="text-sm text-foreground mt-2">{decision.rationale}</p>
              </div>

              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Alternatives Considered
                </p>
                <div className="space-y-3 mt-2">
                  {decision.alternatives.map((alt, idx) => (
                    <div key={idx} className="bg-card/50 p-3 rounded">
                      <p className="font-medium text-sm text-foreground">{alt.name}</p>
                      <div className="mt-2 space-y-1">
                        <p className="text-xs text-emerald-400">
                          <span className="font-semibold">Pros:</span> {alt.pros.join(", ")}
                        </p>
                        <p className="text-xs text-red-400">
                          <span className="font-semibold">Cons:</span> {alt.cons.join(", ")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          <span className="font-semibold">Why not selected:</span>{" "}
                          {alt.reason_not_selected}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

