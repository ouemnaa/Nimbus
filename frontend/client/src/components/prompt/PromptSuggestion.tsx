import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

interface PromptSuggestionProps {
  title: string;
  description: string;
  onClick: () => void;
}

export default function PromptSuggestion({
  title,
  description,
  onClick,
}: PromptSuggestionProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="cursor-pointer"
    >
      <Card className="p-4 h-full bg-gradient-to-b from-[rgba(17,22,29,0.92)] to-[rgba(12,18,26,0.88)] border border-gold-soft/10 hover:border-gold-soft/30 hover:shadow-[0_20px_70px_rgba(228,187,150,0.08)] transition-all duration-300 group">
        <div className="flex items-start gap-2">
          <motion.div animate={{ rotate: [0, 10, 0] }} transition={{ duration: 3, repeat: Infinity }}>
            <Sparkles className="w-4 h-4 text-gold-cloud flex-shrink-0 mt-0.5 group-hover:text-gold-soft transition-colors" />
          </motion.div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-[#F7EEDC] group-hover:text-gold-soft transition-colors">
        {title}
      </h3>
            <p className="text-xs text-[#AFA79A] mt-1 group-hover:text-[#C9BFAF] transition-colors line-clamp-2">
              {description}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
