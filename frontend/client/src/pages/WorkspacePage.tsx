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
import { useLocalStorage } from "@/hooks/useLocalStorage";
import type {
  AnalyzeArchitectureResponse,
  CanonicalArchitecture,
} from "@/types/architecture";
import { ArrowRight } from "lucide-react";
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
  return Array.from(
    markdown.matchAll(/```mermaid\s*([\s\S]*?)```/gi),
    (match) => match[1].trim()
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

export default function WorkspacePage() {
  const { projectId } = useParams();
  const [storedResponse] = useState(loadStoredArchitecture);
  const initialArchitecture = prepareArchitecture(storedResponse);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
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
  const [savedStatus, setSavedStatus] = useLocalStorage(
    `architecture-status-${projectId}`,
    status
  );

  // Load saved status on mount
  useEffect(() => {
    if (savedStatus) {
      updateStatus(savedStatus);
    }
  }, []);

  // Save status to localStorage
  useEffect(() => {
    setSavedStatus(status);
  }, [status, setSavedStatus]);

  const handleFollowUp = () => {
    if (followUp.trim()) {
      setMessages([
        ...messages,
        { role: "user", content: followUp },
        { role: "assistant", content: "Follow-up noted. Architecture updated locally." },
      ]);
      setFollowUp("");
    }
  };

  return (
    <AppShell>
      <div className="flex h-screen bg-transparent">
        {/* Left Panel: Conversation */}
        <div className="w-96 border-r border-gold-soft/10 flex flex-col bg-bg-surface-soft/80 backdrop-blur-md">
          <WorkspaceHeader
            title={architecture.title || "Architecture Workspace"}
            subtitle={`Status: ${status.replace(/_/g, " ")}`}
          />

          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Context Info */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <Card className="p-3 bg-[rgba(17,22,29,0.82)] border border-gold-soft/15 hover:border-gold-soft/30 transition-all duration-300 text-xs shadow-none">
              <div className="space-y-2">
                <div>
                  <span className="text-muted-foreground">Environment:</span>
                  <span className="ml-2 text-foreground">
                    {architecture.requirement_summary.environment}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Budget:</span>
                  <span className="ml-2 text-foreground">
                    {(architecture.requirement_summary.budget_preference ||
                      "not specified").replace(/_/g, " ")}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Cloud:</span>
                  <span className="ml-2 text-foreground">{architecture.cloud.provider}</span>
                </div>
              </div>
              </Card>
            </motion.div>

            {/* Messages */}
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: msg.role === "user" ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4 }}
              >
                <Card
                  className={`p-3 transition-all duration-300 shadow-none ${
                    msg.role === "user"
                      ? "bg-gradient-to-br from-gold-soft/10 to-bronze-muted/10 border border-gold-soft/20 hover:border-gold-soft/40"
                      : "bg-[rgba(17,22,29,0.82)] border border-gold-soft/10 hover:border-gold-soft/30"
                  }`}
                >
                <p className="text-xs font-semibold text-muted-foreground mb-1">
                  {msg.role === "user" ? "You" : "Architect"}
                </p>
                <p className="text-sm text-foreground">{msg.content}</p>
                </Card>
              </motion.div>
            ))}

            {isAnalyzing && <AgentActivity isAnalyzing={isAnalyzing} />}
          </div>

          {/* Follow-up Input */}
          <div className="border-t border-gold-soft/10 p-4 space-y-3 bg-bg-surface-soft/50 backdrop-blur-md">
            <Textarea
              placeholder="Ask about the architecture or request a change…"
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              className="min-h-20 resize-none bg-[rgba(7,9,13,0.62)] border border-gold-soft/15 focus:border-gold-soft/45 focus:shadow-[0_0_15px_rgba(249,217,171,0.15)] transition-all duration-300 text-text-primary"
            />
            <Button
              onClick={handleFollowUp}
              disabled={!followUp.trim()}
              className="w-full gap-2 bg-gradient-to-br from-gold-cloud to-deep-ochre text-bg-main hover:shadow-[0_0_15px_rgba(228,187,150,0.3)] transition-all duration-300 border-none"
            >
              <ArrowRight className="w-4 h-4" />
              Send
            </Button>
          </div>
        </div>

        {/* Right Panel: Architecture Artifact */}
        <div className="flex-1 overflow-hidden">
          <ArchitectureArtifact
            architecture={architecture}
            status={status}
            onStatusChange={updateStatus}
            onArchitectureUpdate={updateArchitecture}
            metadata={storedResponse?.metadata}
          />
        </div>
      </div>
    </AppShell>
  );
}
