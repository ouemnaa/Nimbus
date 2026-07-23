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
      <Card className="p-4 h-full !bg-[#1A2233] border border-[#2A3A52] hover:border-gold-soft/50 hover:shadow-[0_20px_70px_rgba(228,187,150,0.1)] transition-all duration-300 group shadow-lg shadow-black/30">
        <div className="flex items-start gap-3">
          <motion.div animate={{ rotate: [0, 10, 0] }} transition={{ duration: 3, repeat: Infinity }}>
            <Sparkles className="w-4 h-4 text-gold-cloud flex-shrink-0 mt-0.5 group-hover:text-gold-soft transition-colors" />
          </motion.div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-[#F7EEDC] group-hover:text-gold-soft transition-colors leading-snug">
              {title}
            </h3>
            <p className="text-xs text-[#9A9489] mt-1.5 group-hover:text-[#C9BFAF] transition-colors line-clamp-2 leading-relaxed">
              {description}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
