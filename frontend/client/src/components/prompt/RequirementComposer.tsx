import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowRight, Paperclip } from "lucide-react";
import { RequirementContext } from "@/types/architecture";

interface RequirementComposerProps {
  onSubmit: (requirement: string, context: RequirementContext) => void;
  isLoading?: boolean;
}

export default function RequirementComposer({ onSubmit, isLoading }: RequirementComposerProps) {
  const [requirement, setRequirement] = useState("");
  const [context, setContext] = useState<RequirementContext>({
    environment: "development",
    budgetPreference: "BALANCED",
    cloud: "AWS",
    region: "eu-west-1",
  });
  const [showContext, setShowContext] = useState(false);

  const handleSubmit = () => {
    if (requirement.trim()) {
      onSubmit(requirement, context);
    }
  };

  const charCount = requirement.length;
  const maxChars = 5000;
  const showCharCount = charCount > maxChars * 0.8;

  return (
    <div className="space-y-4">
      <div className="bg-card border border-border rounded-lg p-6 shadow-sm">
        <Textarea
          placeholder="Describe the application, expected traffic, environment, budget and technical constraints…"
          value={requirement}
          onChange={(e) => setRequirement(e.target.value)}
          className="min-h-32 resize-none text-base"
          maxLength={maxChars}
        />

        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="w-8 h-8 text-muted-foreground opacity-50 cursor-not-allowed"
              disabled
            >
              <Paperclip className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setShowContext(!showContext)}
            >
              {showContext ? "Hide" : "Set"} context
            </Button>
          </div>

          <div className="flex items-center gap-3">
            {showCharCount && (
              <span className="text-xs text-muted-foreground">
                {charCount} / {maxChars}
              </span>
            )}
            <Button
              onClick={handleSubmit}
              disabled={!requirement.trim() || isLoading}
              className="gap-2"
              size="sm"
            >
              <ArrowRight className="w-4 h-4" />
              Analyze
            </Button>
          </div>
        </div>
      </div>

      {showContext && (
        <div className="bg-card border border-border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Environment</label>
            <select
              value={context.environment}
              onChange={(e) =>
                setContext({ ...context, environment: e.target.value as any })
              }
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Budget Preference</label>
            <select
              value={context.budgetPreference}
              onChange={(e) =>
                setContext({ ...context, budgetPreference: e.target.value as any })
              }
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="MINIMIZE_COST">Minimize Cost</option>
              <option value="BALANCED">Balanced</option>
              <option value="PERFORMANCE_FIRST">Performance First</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Region</label>
            <select
              value={context.region}
              onChange={(e) => setContext({ ...context, region: e.target.value })}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="let-architect-recommend">Let architect recommend</option>
              <option value="eu-west-1">eu-west-1 (Ireland)</option>
              <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
              <option value="us-east-1">us-east-1 (N. Virginia)</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

