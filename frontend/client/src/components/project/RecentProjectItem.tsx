import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatStatus } from "@/utils/format";
import { Link } from "wouter";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

interface RecentProjectItemProps {
  id: string;
  title: string;
  status: string;
  updatedAt: Date;
}

export default function RecentProjectItem({
  id,
  title,
  status,
  updatedAt,
}: RecentProjectItemProps) {
  const statusColor =
    status === "APPROVED"
      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
      : status === "READY_FOR_REVIEW"
        ? "bg-amber-500/10 text-amber-700 dark:text-gold-cloud border border-amber-500/20"
        : "bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20";

  return (
    <Link href={`/workspace/${id}`}>
      <motion.div
        whileHover={{ scale: 1.02, y: -4 }}
        whileTap={{ scale: 0.98 }}
        className="cursor-pointer"
      >
        <Card className="p-3 h-full bg-card border border-border hover:border-gold-soft/50 transition-all duration-300 group shadow-sm hover:shadow-md">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-sm text-text-primary group-hover:text-gold-soft transition-colors truncate flex items-center gap-2">
              {title}
              <motion.div animate={{ x: [0, 4, 0] }} transition={{ duration: 2, repeat: Infinity }}>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </motion.div>
            </h4>
            <p className="text-xs text-text-muted mt-1">{formatDate(updatedAt)}</p>
          </div>
          <Badge className={`${statusColor} text-xs whitespace-nowrap bg-transparent shadow-none`}>
            {formatStatus(status)}
          </Badge>
        </div>
        </Card>
      </motion.div>
    </Link>
  );
}
