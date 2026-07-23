import { useState } from "react";
import { useLocation } from "wouter";
import AppShell from "@/components/layout/AppShell";
import PromptSuggestion from "@/components/prompt/PromptSuggestion";
import RecentProjectItem from "@/components/project/RecentProjectItem";
import { promptSuggestions } from "@/data/promptSuggestions";
import { mockProjects } from "@/data/mockArchitecture";
import { architectureService } from "@/services/mockArchitectureService";
import { RequirementContext } from "@/types/architecture";
import { BoltStyleChat } from "@/components/ui/bolt-style-chat";
import { motion } from "framer-motion";

export default function HomePage() {
  const [, navigate] = useLocation();
  const [, setIsAnalyzing] = useState(false);

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
      <div className="flex-1 overflow-auto bg-transparent">
        <div className="relative">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <BoltStyleChat
              onSend={handleChatSubmit}
              announcementText="Nimbus Solution Architect"
              title="What will you"
              subtitle="Turn your product idea into a review-ready cloud architecture in one conversation."
              placeholder="Describe your application requirements and goals. For example: low-cost AWS platform with ECS, PostgreSQL, private networking, and room to scale."
              fullBleed
            />
          </motion.div>

          <div className="relative z-10 -mt-14 px-6 pb-16">
            <div className="mx-auto max-w-6xl">
              <motion.div
                className="mb-16"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.4 }}
              >
                <h2 className="mb-6 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                  Example Requirements
                </h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  {promptSuggestions.map((suggestion, idx) => (
                    <motion.div
                      key={suggestion.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.4 + idx * 0.1 }}
                    >
                      <PromptSuggestion
                        title={suggestion.title}
                        description={suggestion.description}
                        onClick={() => handleChatSubmit(suggestion.description)}
                      />
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.5 }}
              >
                <h2 className="mb-6 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                  Recent Architectures
                </h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {mockProjects.slice(0, 2).map((project, idx) => (
                    <motion.div
                      key={project.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.5 + idx * 0.1 }}
                    >
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
        </div>
      </div>
    </AppShell>
  );
}
