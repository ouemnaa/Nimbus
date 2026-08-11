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
      <Card className="p-4 h-full bg-card border border-border hover:border-gold-soft/50 transition-all duration-300 group shadow-sm hover:shadow-md">
        <div className="flex items-start gap-3">
          <motion.div animate={{ rotate: [0, 10, 0] }} transition={{ duration: 3, repeat: Infinity }}>
            <Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5 group-hover:text-gold-soft transition-colors" />
          </motion.div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-text-primary group-hover:text-gold-soft transition-colors leading-snug">
              {title}
            </h3>
            <p className="text-xs text-text-muted mt-1.5 group-hover:text-text-secondary transition-colors line-clamp-2 leading-relaxed">
              {description}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
