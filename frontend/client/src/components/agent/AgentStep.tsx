import { Check, Clock, Zap } from "lucide-react";

type StepStatus = "pending" | "active" | "completed";

interface AgentStepProps {
  status: StepStatus;
  title: string;
  description?: string;
}

export default function AgentStep({ status, title, description }: AgentStepProps) {
  const statusIcon =
    status === "completed" ? (
      <Check className="w-4 h-4 text-emerald-400" />
    ) : status === "active" ? (
      <Zap className="w-4 h-4 text-gold-soft animate-pulse" />
    ) : (
      <Clock className="w-4 h-4 text-muted-foreground" />
    );

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 mt-1">{statusIcon}</div>
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </div>
    </div>
  );
}

