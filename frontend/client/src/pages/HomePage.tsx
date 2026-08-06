import { useState } from "react";
import { useLocation } from "wouter";
import AppShell from "@/components/layout/AppShell";
import PromptSuggestion from "@/components/prompt/PromptSuggestion";
import RecentProjectItem from "@/components/project/RecentProjectItem";
import { promptSuggestions } from "@/data/promptSuggestions";
import { mockProjects } from "@/data/mockArchitecture";
import { architectureService as demoArchitectureService } from "@/services/mockArchitectureService";
import {
  analyzeArchitecture,
  NIMBUS_BACKEND_URL,
} from "@/services/architectureService";
import { AnalyzeArchitectureResponse, RequirementContext } from "@/types/architecture";
import { BoltStyleChat } from "@/components/ui/bolt-style-chat";
import AgentActivity from "@/components/agent/AgentActivity";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function HomePage() {
  const [, navigate] = useLocation();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSubmission, setLastSubmission] = useState<{
    requirement: string;
    context: RequirementContext;
  } | null>(null);

  const saveAndOpenWorkspace = (
    response: AnalyzeArchitectureResponse & { projectId?: string },
    requirement: string
  ) => {
    localStorage.setItem("nimbus:lastArchitecture", JSON.stringify(response));
    localStorage.setItem("nimbus:lastRequirement", requirement);
    const projectId = response.projectId || "latest";
    navigate(`/workspace/${encodeURIComponent(projectId)}`);
  };

  const handleAnalyze = async (
    requirement: string,
    context: RequirementContext
  ): Promise<boolean> => {
    const trimmedRequirement = requirement.trim();
    if (!trimmedRequirement) {
      setError("Describe what you want to design before submitting.");
      return false;
    }

    const submission = { requirement: trimmedRequirement, context };
    setLastSubmission(submission);
    setIsAnalyzing(true);
    setError(null);
    try {
      const response = await analyzeArchitecture(submission);
      saveAndOpenWorkspace(response, trimmedRequirement);
      return true;
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : `Could not reach the Nimbus backend. Make sure it is running on ${NIMBUS_BACKEND_URL}.`
      );
      return false;
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleChatSubmit = (value: string) => {
    const context: RequirementContext = {
      environment: "development",
      budget_preference: "low",
      cloud: "AWS",
      region: "eu-west-1",
    };
    return handleAnalyze(value, context);
  };

  const handleUseDemoData = async () => {
    const submission = lastSubmission || {
      requirement:
        "Deploy a small containerized web application with PostgreSQL on AWS. This is a development environment and cost should remain low.",
      context: {
        environment: "development" as const,
        budget_preference: "low",
        cloud: "AWS" as const,
        region: "eu-west-1",
      },
    };

    setError(null);
    setIsAnalyzing(true);
    try {
      const response =
        await demoArchitectureService.analyzeRequirement(submission);
      saveAndOpenWorkspace(response, submission.requirement);
    } finally {
      setIsAnalyzing(false);
    }
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
              isLoading={isAnalyzing}
              feedback={
                isAnalyzing ? (
                  <div className="mx-auto w-full max-w-[720px] text-left">
                    <AgentActivity isAnalyzing />
                  </div>
                ) : error ? (
                  <div className="mx-auto w-full max-w-[720px] rounded-2xl border border-red-400/25 bg-red-950/20 p-4 text-left backdrop-blur-md">
                    <div className="flex gap-3">
                      <AlertCircle className="mt-0.5 size-5 shrink-0 text-red-300" />
                      <div className="space-y-3">
                        <p className="text-sm text-text-primary">{error}</p>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            onClick={() =>
                              lastSubmission &&
                              handleAnalyze(
                                lastSubmission.requirement,
                                lastSubmission.context
                              )
                            }
                            disabled={!lastSubmission}
                          >
                            Try again
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleUseDemoData}
                          >
                            Use demo data
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : undefined
              }
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
