import { Button } from "@/components/ui/button";
import { ArchitectureStatus } from "@/types/architecture";

interface ReviewBarProps {
  status: ArchitectureStatus;
  onApprove: () => void;
  onEdit: () => void;
  onRedesign: () => void;
}

export default function ReviewBar({
  status,
  onApprove,
  onEdit,
  onRedesign,
}: ReviewBarProps) {
  if (status === "APPROVED") {
    return (
      <div className="border-t border-border bg-emerald-500/5 px-6 py-4">
        <p className="text-sm text-emerald-400">
          ✓ Architecture approved and locked for generation.
        </p>
      </div>
    );
  }

  return (
    <div className="border-t border-border bg-background px-6 py-4 flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        {status === "READY_FOR_REVIEW"
          ? "Architecture ready for review"
          : "Clarification needed"}
      </p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onEdit}>
          Edit properties
        </Button>
        <Button variant="outline" size="sm" onClick={onRedesign}>
          Request redesign
        </Button>
        <Button size="sm" onClick={onApprove}>
          Approve architecture
        </Button>
      </div>
    </div>
  );
}

