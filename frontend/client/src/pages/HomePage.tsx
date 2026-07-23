import { useState } from "react";
import { useLocation } from "wouter";
import AppShell from "@/components/layout/AppShell";
import PromptSuggestion from "@/components/prompt/PromptSuggestion";
import RecentProjectItem from "@/components/project/RecentProjectItem";
import { brand } from "@/config/brand";
import { promptSuggestions } from "@/data/promptSuggestions";
import { mockProjects } from "@/data/mockArchitecture";
import { architectureService } from "@/services/mockArchitectureService";
import { RequirementContext } from "@/types/architecture";
import { VercelV0Chat } from "@/components/ui/v0-ai-chat";
import { motion } from "framer-motion";
import { VercelV0Chat as VercelV0ChatModern } from "@/components/ui/v0-ai-chat-modern";

export default function HomePage() {
  const [, navigate] = useLocation();
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async (requirement: string, context: RequirementContext) => {
    setIsAnalyzing(true);
    try {
      const response = await architectureService.analyzeRequirement({
        requirement,
        context,
      });
      navigate(`/workspace/${response.projectId}`);
    } catch (error) {
      console.error("Analysis failed:", error);
      setIsAnalyzing(false);
    }
  };

  const handleChatSubmit = (value: string) => {
    const context: RequirementContext = {
      environment: "production",
      budgetPreference: "BALANCED",
      cloud: "AWS",
      region: "eu-west-1",
    };
    handleAnalyze(value, context);
  };

  return (
    <AppShell>
      <div className="flex-1 overflow-auto bg-gradient-to-b from-background via-background to-primary/5">
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <motion.div
            className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-primary/20 to-transparent rounded-full blur-3xl"
            animate={{ y: [0, 50, 0], x: [0, 30, 0] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-accent/20 to-transparent rounded-full blur-3xl"
            animate={{ y: [0, -50, 0], x: [0, -30, 0] }}
            transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        <div className="relative z-10 max-w-5xl mx-auto px-6 py-16">
          <motion.div className="text-center mb-16" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <motion.h1 className="text-6xl md:text-7xl font-black text-foreground mb-4 bg-gradient-to-r from-foreground via-primary to-accent bg-clip-text text-transparent" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.1 }}>
              What are you building?
            </motion.h1>
            <motion.p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}>
              Describe your application, constraints and goals. Your Solution Architect will turn them into a reviewable cloud design.
            </motion.p>
          </motion.div>
          <motion.div className="mb-20" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.3 }}>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/50 via-accent/50 to-primary/50 rounded-2xl blur-xl opacity-50" />
              <div className="relative bg-background/80 backdrop-blur-xl rounded-2xl border border-primary/20">
            <VercelV0ChatModern
              onSubmit={handleChatSubmit}
              title=""
              placeholder="Describe your application, constraints and goals. Your Solution Architect will turn them into a reviewable cloud design."
            />
              </div>
            </div>
          </motion.div>

          {/* Prompt Suggestions */}
          <motion.div className="mb-16" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.4 }}>
            <h2 className="text-sm font-semibold text-muted-foreground mb-6 uppercase tracking-widest">
              Example Requirements
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {promptSuggestions.map((suggestion, idx) => (
                <motion.div key={suggestion.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.4 + idx * 0.1 }}>
                <PromptSuggestion
                  title={suggestion.title}
                  description={suggestion.description}
                  onClick={() => handleChatSubmit(suggestion.description)}
                />
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Recent Architectures */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.5 }}>
            <h2 className="text-sm font-semibold text-muted-foreground mb-6 uppercase tracking-widest">
              Recent Architectures
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {mockProjects.slice(0, 2).map((project, idx) => (
                <motion.div key={project.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.5 + idx * 0.1 }}>
                <RecentProjectItem
                  id={project.id}
                  title={project.title}
                  status={project.status}
                  updatedAt={project.updatedAt}
                />
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </AppShell>
  );
}
