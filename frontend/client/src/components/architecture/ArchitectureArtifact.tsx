import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Copy, Download, MoreHorizontal } from "lucide-react";
import { CanonicalArchitecture, ArchitectureStatus as ArchitectureStatusType } from "@/types/architecture";
import { motion } from "framer-motion";
import ArchitectureStatusBadge from "./ArchitectureStatus";
import ArchitectureOverview from "./ArchitectureOverview";
import ArchitectureDiagram from "./ArchitectureDiagram";
import ArchitectureComponents from "./ArchitectureComponents";
import ArchitectureDecisions from "./ArchitectureDecisions";
import ArchitectureReport from "./ArchitectureReport";
import ArchitectureJson from "./ArchitectureJson";
import ReviewBar from "../review/ReviewBar";
import ApproveDialog from "../review/ApproveDialog";
import EditArchitectureDrawer from "../review/EditArchitectureDrawer";
import RedesignDialog from "../review/RedesignDialog";
import { downloadFile, slugify } from "@/utils/download";
import { toast } from "sonner";

interface ArchitectureArtifactProps {
  architecture: CanonicalArchitecture;
  status: ArchitectureStatusType;
  onStatusChange: (status: ArchitectureStatusType) => void;
  onArchitectureUpdate: (updates: Partial<CanonicalArchitecture>) => void;
}

export default function ArchitectureArtifact({
  architecture,
  status,
  onStatusChange,
  onArchitectureUpdate,
}: ArchitectureArtifactProps) {
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [redesignDialogOpen, setRedesignDialogOpen] = useState(false);

  const handleApprove = () => {
    onStatusChange("APPROVED");
    setApproveDialogOpen(false);
    toast.success("Architecture approved");
  };

  const handleRedesign = (feedback: string, targetArea: string) => {
    toast.success("Redesign request captured. Backend integration will be added later.");
  };

  const handleDownloadMarkdown = () => {
    if (architecture.markdown_report) {
      downloadFile(
        architecture.markdown_report,
        `${slugify(architecture.title)}.md`,
        "text/markdown"
      );
      toast.success("Markdown report downloaded");
    }
  };

  const handleCopyReport = () => {
    if (architecture.markdown_report) {
      navigator.clipboard.writeText(architecture.markdown_report);
      toast.success("Markdown report copied to clipboard");
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <div className="border-b border-border/50 px-6 py-4 bg-background/80 backdrop-blur-sm">
        <motion.div
          className="flex items-start justify-between gap-4 mb-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
              {architecture.title}
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <ArchitectureStatusBadge status={status} />
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">
                {architecture.cloud.provider} • {architecture.cloud.region} •{" "}
                {architecture.requirement_summary.environment}
              </span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">Generated just now</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-2 hover:bg-primary/10 hover:border-primary/50 transition-all duration-200"
              onClick={handleCopyReport}
            >
              <Copy className="w-4 h-4" />
              Copy report
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 hover:bg-primary/10 hover:border-primary/50 transition-all duration-200"
              onClick={handleDownloadMarkdown}
            >
              <Download className="w-4 h-4" />
              Download
            </Button>
            <Button variant="outline" size="icon" className="hover:bg-primary/10 hover:border-primary/50 transition-all duration-200">
              <MoreHorizontal className="w-4 h-4" />
            </Button>
          </div>
        </motion.div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="flex-1 overflow-hidden flex flex-col">
        <TabsList className="w-full justify-start border-b border-border/50 bg-background/50 backdrop-blur-sm px-6 rounded-none h-auto p-0">
          <TabsTrigger value="overview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Overview
          </TabsTrigger>
          <TabsTrigger value="diagram" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Diagram
          </TabsTrigger>
          <TabsTrigger value="components" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Components
          </TabsTrigger>
          <TabsTrigger value="decisions" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Decisions
          </TabsTrigger>
          <TabsTrigger value="report" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Report
          </TabsTrigger>
          <TabsTrigger value="specification" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
            Specification
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-auto">
          <div className="px-6 py-6">
            <TabsContent value="overview" className="mt-0">
              <ArchitectureOverview architecture={architecture} />
            </TabsContent>

            <TabsContent value="diagram" className="mt-0 space-y-4">
              {architecture.high_level_diagram && (
                <ArchitectureDiagram
                  diagram={architecture.high_level_diagram}
                  title="High-Level Architecture"
                />
              )}
              {architecture.network_diagram && (
                <ArchitectureDiagram
                  diagram={architecture.network_diagram}
                  title="Network Architecture"
                />
              )}
            </TabsContent>

            <TabsContent value="components" className="mt-0">
              <ArchitectureComponents components={architecture.resources} />
            </TabsContent>

            <TabsContent value="decisions" className="mt-0">
              <ArchitectureDecisions decisions={architecture.decisions} />
            </TabsContent>

            <TabsContent value="report" className="mt-0">
              {architecture.markdown_report && (
                <ArchitectureReport markdown={architecture.markdown_report} />
              )}
            </TabsContent>

            <TabsContent value="specification" className="mt-0">
              <ArchitectureJson architecture={architecture} />
            </TabsContent>
          </div>
        </div>
      </Tabs>

      {/* Review Bar */}
      <ReviewBar
        status={status}
        onApprove={() => setApproveDialogOpen(true)}
        onEdit={() => setEditDrawerOpen(true)}
        onRedesign={() => setRedesignDialogOpen(true)}
      />

      {/* Dialogs */}
      <ApproveDialog
        open={approveDialogOpen}
        onOpenChange={setApproveDialogOpen}
        onConfirm={handleApprove}
      />
      <EditArchitectureDrawer
        open={editDrawerOpen}
        onOpenChange={setEditDrawerOpen}
        architecture={architecture}
        onSave={onArchitectureUpdate}
      />
      <RedesignDialog
        open={redesignDialogOpen}
        onOpenChange={setRedesignDialogOpen}
        onSubmit={handleRedesign}
      />
    </div>
  );
}
