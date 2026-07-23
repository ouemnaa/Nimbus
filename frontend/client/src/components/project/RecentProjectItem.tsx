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
      ? "bg-emerald-500/10 text-emerald-400"
      : status === "READY_FOR_REVIEW"
        ? "bg-gold-soft/10 text-gold-cloud"
        : "bg-amber-500/10 text-amber-400";

  return (
    <Link href={`/workspace/${id}`}>
      <motion.div
        whileHover={{ scale: 1.02, y: -4 }}
        whileTap={{ scale: 0.98 }}
        className="cursor-pointer"
      >
        <Card className="p-3 h-full !bg-[#1A2233] border border-[#2A3A52] hover:border-gold-soft/50 hover:shadow-[0_20px_70px_rgba(228,187,150,0.1)] transition-all duration-300 group shadow-lg shadow-black/30">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-sm text-[#F7EEDC] group-hover:text-gold-soft transition-colors truncate flex items-center gap-2">
              {title}
              <motion.div animate={{ x: [0, 4, 0] }} transition={{ duration: 2, repeat: Infinity }}>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </motion.div>
            </h4>
            <p className="text-xs text-[#AFA79A] mt-1">{formatDate(updatedAt)}</p>
          </div>
          <Badge className={`${statusColor} text-xs whitespace-nowrap`}>
            {formatStatus(status)}
          </Badge>
        </div>
        </Card>
      </motion.div>
    </Link>
  );
}
