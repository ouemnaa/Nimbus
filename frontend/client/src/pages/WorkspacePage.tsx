import { useState, useEffect } from "react";
import { useParams } from "wouter";
import AppShell from "@/components/layout/AppShell";
import WorkspaceHeader from "@/components/layout/WorkspaceHeader";
import AgentActivity from "@/components/agent/AgentActivity";
import ArchitectureArtifact from "@/components/architecture/ArchitectureArtifact";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { mockArchitecture } from "@/data/mockArchitecture";
import { useArchitecture } from "@/hooks/useArchitecture";
import {
  acceptDraftVersion,
  discardDraftVersion,
  generateTerraform,
  getLatestTerraformGeneration,
  getProjectWorkspace,
  sendProjectMessage,
  updateArchitectureStatus,
} from "@/services/architectureService";
import type {
  AnalyzeArchitectureResponse,
  BackendArchitectureVersion,
  CanonicalArchitecture,
  ProjectWorkspaceResponse,
  TerraformGeneration,
} from "@/types/architecture";
import { AlertCircle, ArrowRight, ChevronLeft, ChevronRight, MessageSquare } from "lucide-react";
import { motion } from "framer-motion";

function loadStoredArchitecture(): AnalyzeArchitectureResponse | null {
  try {
    const stored = localStorage.getItem("nimbus:lastArchitecture");
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored) as Partial<AnalyzeArchitectureResponse>;
    return parsed.architecture && typeof parsed.architecture === "object"
      ? (parsed as AnalyzeArchitectureResponse)
      : null;
  } catch {
    return null;
  }
}

function extractMermaidDiagrams(markdown: string): string[] {
  return Array.from(markdown.matchAll(/```mermaid\s*([\s\S]*?)```/gi), match =>
    match[1].trim()
  );
}

function prepareArchitecture(
  response: AnalyzeArchitectureResponse | null
): CanonicalArchitecture {
  if (!response) {
    return mockArchitecture;
  }

  const architecture = response.architecture;
  const diagrams = extractMermaidDiagrams(response.report_markdown || "");

  return {
    ...architecture,
    title: architecture.title || "Generated Cloud Architecture",
    status: architecture.status || "READY_FOR_REVIEW",
    requirement_summary: {
      business_goal:
        architecture.requirement_summary?.business_goal || "Not provided",
      application_type:
        architecture.requirement_summary?.application_type || "Not provided",
      environment:
        architecture.requirement_summary?.environment || "development",
      expected_users_or_traffic:
        architecture.requirement_summary?.expected_users_or_traffic ||
        "Not provided",
      functional_requirements:
        architecture.requirement_summary?.functional_requirements || [],
      non_functional_requirements:
        architecture.requirement_summary?.non_functional_requirements || [],
      constraints: architecture.requirement_summary?.constraints || [],
      budget_preference:
        architecture.requirement_summary?.budget_preference || "not specified",
      availability_requirement:
        architecture.requirement_summary?.availability_requirement ||
        "not specified",
    },
    cloud: {
      provider: architecture.cloud?.provider || "AWS",
      region: architecture.cloud?.region || "Not specified",
      region_rationale: architecture.cloud?.region_rationale || "Not provided",
    },
    solution: architecture.solution || "No solution summary was returned.",
    resources: architecture.resources || [],
    relationships: architecture.relationships || [],
    decisions: architecture.decisions || [],
    security_considerations: architecture.security_considerations || [],
    reliability_considerations: architecture.reliability_considerations || [],
    scalability_considerations: architecture.scalability_considerations || [],
    cost_considerations: architecture.cost_considerations || [],
    operational_considerations: architecture.operational_considerations || [],
    assumptions: architecture.assumptions || [],
    open_questions: architecture.open_questions || [],
    risks: architecture.risks || [],
    limitations: architecture.limitations || [],
    recommended_diagrams: architecture.recommended_diagrams || [],
    markdown_report: response.report_markdown || "",
    high_level_diagram: architecture.high_level_diagram || diagrams[0],
    network_diagram: architecture.network_diagram || diagrams[1],
  };
}

function prepareWorkspaceArchitecture(
  workspace: ProjectWorkspaceResponse
): CanonicalArchitecture {
  const version = workspace.currentVersion;
  if (!version) {
    return mockArchitecture;
  }

  return prepareArchitecture({
    architecture: version.architecture,
    report_markdown: version.reportMarkdown,
    metadata: version.metadata as AnalyzeArchitectureResponse["metadata"],
  });
}

export default function WorkspacePage() {
  const { projectId } = useParams();
  const [storedResponse] = useState(loadStoredArchitecture);
  const initialArchitecture = prepareArchitecture(storedResponse);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [draftVersion, setDraftVersion] =
    useState<BackendArchitectureVersion | null>(null);
  const [currentVersionId, setCurrentVersionId] = useState<string | null>(null);
  const [terraformGeneration, setTerraformGeneration] =
    useState<TerraformGeneration | null>(null);
  const [isGeneratingTerraform, setIsGeneratingTerraform] = useState(false);
  const [messages, setMessages] = useState<
    Array<{ role: string; content: string }>
  >([
    {
      role: "user",
      content:
        localStorage.getItem("nimbus:lastRequirement") ||
        "Design AWS infrastructure for a small containerized web application with PostgreSQL.",
    },
    {
      role: "assistant",
      content: "Analysis complete. Architecture ready for review.",
    },
  ]);
  const [followUp, setFollowUp] = useState("");
  const { architecture, status, updateStatus, updateArchitecture } =
    useArchitecture(initialArchitecture);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    let isMounted = true;
    setIsAnalyzing(true);
    setError(null);

    Promise.all([
      getProjectWorkspace(projectId),
      getLatestTerraformGeneration(projectId),
    ])
      .then(([workspace, latestTerraform]) => {
        if (!isMounted) {
          return;
        }
        const loadedArchitecture = prepareWorkspaceArchitecture(workspace);
        updateArchitecture(loadedArchitecture);
        updateStatus(loadedArchitecture.status);
        setCurrentVersionId(workspace.currentVersion?.id ?? null);
        setMessages(
          workspace.messages.map(message => ({
            role: message.role,
            content: message.content,
          }))
        );
        setDraftVersion(
          workspace.versions.find(
            version => version.status === "DRAFT_REVISION"
          ) || null
        );
        setTerraformGeneration(latestTerraform);
      })
      .catch(error => {
        if (isMounted) {
          setError(
            error instanceof Error ? error.message : "Could not load workspace."
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsAnalyzing(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [projectId, updateArchitecture, updateStatus]);

  const handleFollowUp = async () => {
    const trimmed = followUp.trim();
    if (!trimmed || !projectId) {
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setFollowUp("");

    try {
      const response = await sendProjectMessage(projectId, trimmed);
      setMessages(
        response.messages.map(message => ({
          role: message.role,
          content: message.content,
        }))
      );
      if (response.architectureChanged && response.draftVersion) {
        setDraftVersion(response.draftVersion);
      }
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Could not send message."
      );
      setFollowUp(trimmed);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const applyWorkspace = (workspace: ProjectWorkspaceResponse) => {
    const loadedArchitecture = prepareWorkspaceArchitecture(workspace);
    updateArchitecture(loadedArchitecture);
    updateStatus(loadedArchitecture.status);
    setMessages(
      workspace.messages.map(message => ({
        role: message.role,
        content: message.content,
      }))
    );
    setDraftVersion(
      workspace.versions.find(version => version.status === "DRAFT_REVISION") ||
        null
    );
  };

  const handleAcceptDraft = async () => {
    if (!projectId || !draftVersion) {
      return;
    }
    setIsAnalyzing(true);
    setError(null);
    try {
      applyWorkspace(await acceptDraftVersion(projectId, draftVersion.id));
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Could not accept draft."
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDiscardDraft = async () => {
    if (!projectId || !draftVersion) {
      return;
    }
    setIsAnalyzing(true);
    setError(null);
    try {
      applyWorkspace(await discardDraftVersion(projectId, draftVersion.id));
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Could not discard draft."
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateTerraform = async () => {
    if (!projectId) {
      return;
    }
    setIsGeneratingTerraform(true);
    setError(null);
    try {
      setTerraformGeneration(await generateTerraform(projectId));
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Could not generate Terraform."
      );
    } finally {
      setIsGeneratingTerraform(false);
    }
  };

  return (
    <AppShell>
      <div className="flex h-screen bg-transparent relative">
        {/* Left Panel: Conversation */}
        <div className={`${isSidebarCollapsed ? "w-16" : "w-96"} transition-all duration-300 border-r border-border/40 flex flex-col bg-bg-surface-soft/80 backdrop-blur-md relative z-10 shrink-0`}>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="absolute -right-4 top-6 z-20 w-8 h-8 rounded-full bg-card border border-border/40 shadow-md flex items-center justify-center hover:bg-accent hover:text-accent-foreground"
          >
            {isSidebarCollapsed ? <ChevronRight className="w-4 h-4"/> : <ChevronLeft className="w-4 h-4"/>}
          </Button>

          {isSidebarCollapsed ? (
            <div className="flex flex-col items-center py-6 gap-6 h-full">
              <MessageSquare className="w-6 h-6 text-primary" />
            </div>
          ) : (
            <>
              <WorkspaceHeader
                title={architecture.title || "Architecture Workspace"}
                subtitle={`Status: ${status.replace(/_/g, " ")}`}
              />

              <div className="flex-1 overflow-auto p-5 space-y-2 workspace-scrollbar">
                {/* Context Info Bento */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="grid grid-cols-3 gap-2 mb-6">
                      <div className="flex flex-col p-3 rounded-xl dark:bg-black/20 bg-black/5 dark:border-white/5 border-black/5 shadow-inner">
                        <span className="text-[9px] text-muted-foreground uppercase tracking-widest font-bold mb-1">Env</span>
                        <span className="text-xs dark:text-slate-200 text-slate-800 font-medium truncate">{architecture.requirement_summary.environment}</span>
                      </div>
                      <div className="flex flex-col p-3 rounded-xl dark:bg-black/20 bg-black/5 dark:border-white/5 border-black/5 shadow-inner">
                        <span className="text-[9px] text-muted-foreground uppercase tracking-widest font-bold mb-1">Budget</span>
                        <span className="text-xs dark:text-slate-200 text-slate-800 font-medium truncate">{(architecture.requirement_summary.budget_preference || "not specified").replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex flex-col p-3 rounded-xl dark:bg-black/20 bg-black/5 dark:border-white/5 border-black/5 shadow-inner">
                        <span className="text-[9px] text-muted-foreground uppercase tracking-widest font-bold mb-1">Cloud</span>
                        <span className="text-xs dark:text-slate-200 text-slate-800 font-medium truncate">{architecture.cloud.provider}</span>
                      </div>
                  </div>
                </motion.div>

                {error && (
                  <div className="flex gap-3 items-center border border-red-500/30 dark:bg-red-500/10 bg-red-50 p-3 rounded-xl text-xs dark:text-red-200 text-red-700 mb-6">
                    <AlertCircle className="size-4 shrink-0 dark:text-red-400 text-red-600" />
                    <span className="leading-relaxed">{error}</span>
                  </div>
                )}

                {draftVersion && (
                  <div className="border border-primary/30 dark:bg-primary/10 bg-primary/5 p-4 rounded-xl mb-6 shadow-lg backdrop-blur-sm">
                    <p className="text-sm font-bold dark:text-slate-100 text-slate-900 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                      Draft Update Ready
                    </p>
                    <p className="mt-1.5 text-xs dark:text-slate-300 text-slate-600">
                      Version {draftVersion.version} is ready for review.
                    </p>
                    <div className="mt-4 flex gap-2">
                      <Button
                        size="sm"
                        className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90 text-xs shadow-md"
                        onClick={handleAcceptDraft}
                        disabled={isAnalyzing}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 dark:border-white/10 border-black/10 dark:hover:bg-white/5 hover:bg-black/5 text-xs"
                        onClick={handleDiscardDraft}
                        disabled={isAnalyzing}
                      >
                        Discard
                      </Button>
                    </div>
                  </div>
                )}

                {/* Messages */}
                <div className="space-y-6 pb-4">
                  {messages.map((msg, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4 }}
                      className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
                    >
                      <div className="flex items-center gap-2 mb-1.5 px-1">
                         <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                           {msg.role === "user" ? "You" : "Architect"}
                         </span>
                      </div>
                      <div
                        className={`relative max-w-[90%] p-4 text-[13px] leading-relaxed shadow-xl ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm"
                            : "dark:bg-white/5 bg-black/5 dark:text-slate-200 text-slate-800 dark:border-white/10 border-black/5 rounded-2xl rounded-tl-sm backdrop-blur-md border"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    </motion.div>
                  ))}
                  {isAnalyzing && (
                    <div className="flex justify-start">
                      <div className="dark:bg-white/5 bg-black/5 dark:border-white/10 border-black/5 rounded-2xl rounded-tl-sm p-4 backdrop-blur-md border">
                        <AgentActivity isAnalyzing={isAnalyzing} />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Follow-up Input */}
              <div className="p-4 bg-background/60 backdrop-blur-xl border-t border-border/40">
                <div className="relative group">
                  <Textarea
                    placeholder="Ask about the architecture..."
                    value={followUp}
                    onChange={e => setFollowUp(e.target.value)}
                    className="min-h-[60px] pr-12 resize-none rounded-xl dark:bg-black/40 bg-white/80 dark:border-white/10 border-black/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all duration-300 dark:text-slate-200 text-slate-900 dark:placeholder:text-slate-500 placeholder-slate-400 workspace-scrollbar text-sm py-3.5 shadow-inner"
                  />
                  <Button
                    size="icon"
                    onClick={handleFollowUp}
                    disabled={!followUp.trim() || isAnalyzing}
                    className="absolute right-2 bottom-2 w-8 h-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md disabled:opacity-50"
                  >
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Panel: Architecture Artifact */}
        <div className="flex-1 overflow-hidden">
          <ArchitectureArtifact
            architecture={architecture}
            status={status}
            onStatusChange={async (newStatus) => {
              updateStatus(newStatus);
              if (projectId && currentVersionId) {
                try {
                  await updateArchitectureStatus(projectId, currentVersionId, newStatus);
                } catch {
                  // status already updated locally; backend failure is non-blocking
                }
              }
            }}
            onArchitectureUpdate={updateArchitecture}
            metadata={storedResponse?.metadata}
            terraformGeneration={terraformGeneration}
            isGeneratingTerraform={isGeneratingTerraform}
            onGenerateTerraform={handleGenerateTerraform}
          />
        </div>
      </div>
    </AppShell>
  );
}
