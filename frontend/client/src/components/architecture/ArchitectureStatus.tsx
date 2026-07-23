import { Badge } from "@/components/ui/badge";
import { ArchitectureStatus as ArchitectureStatusType } from "@/types/architecture";

interface ArchitectureStatusBadgeProps {
  status: ArchitectureStatusType;
}

const styles: Record<ArchitectureStatusType, string> = {
  READY_FOR_REVIEW: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  APPROVED: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  NEEDS_CLARIFICATION: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  UNSUPPORTED: "bg-red-500/10 text-red-300 border-red-500/30",
};

export default function ArchitectureStatusBadge({
  status,
}: ArchitectureStatusBadgeProps) {
  return (
    <Badge variant="outline" className={styles[status]}>
      {status.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase())}
    </Badge>
  );
}
