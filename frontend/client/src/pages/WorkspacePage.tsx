import { useState, useEffect } from "react";
import { useParams } from "wouter";
import AppShell from "@/components/layout/AppShell";
import WorkspaceHeader from "@/components/layout/WorkspaceHeader";
import AgentActivity from "@/components/agent/AgentActivity";
import ArchitectureArtifact from "@/components/architecture/ArchitectureArtifact";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { mockArchitecture, mockProjects } from "@/data/mockArchitecture";
import { useArchitecture } from "@/hooks/useArchitecture";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function WorkspacePage() {
  const { projectId } = useParams();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    {
      role: "user",
      content:
        "Design AWS infrastructure for a small containerized web application with PostgreSQL. This is a development environment and cost should remain low.",
    },
    {
      role: "assistant",
      content: "Analysis complete. Architecture ready for review.",
    },
  ]);
  const [followUp, setFollowUp] = useState("");
  const { architecture, status, updateStatus, updateArchitecture } =
    useArchitecture(mockArchitecture);
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

  const project = mockProjects.find((p) => p.id === projectId);

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
            title={project?.title || "Architecture Workspace"}
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
                    {architecture.requirement_summary.budget_preference.replace(/_/g, " ")}
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
          />
        </div>
      </div>
    </AppShell>
  );
}
