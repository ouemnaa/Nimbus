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
      <Card className="p-4 h-full bg-gradient-to-br from-card to-card/50 hover:from-primary/10 hover:to-accent/10 border border-border/50 hover:border-primary/50 transition-all duration-300 group">
        <div className="flex items-start gap-2">
          <motion.div animate={{ rotate: [0, 10, 0] }} transition={{ duration: 3, repeat: Infinity }}>
            <Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
          </motion.div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors">
        {title}
      </h3>
            <p className="text-xs text-muted-foreground mt-1 group-hover:text-foreground/70 transition-colors line-clamp-2">
              {description}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
