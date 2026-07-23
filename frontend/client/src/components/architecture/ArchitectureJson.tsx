import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Copy, Download } from "lucide-react";
import { CanonicalArchitecture } from "@/types/architecture";
import { downloadFile } from "@/utils/download";
import { toast } from "sonner";

interface ArchitectureJsonProps {
  architecture: CanonicalArchitecture;
}

export default function ArchitectureJson({ architecture }: ArchitectureJsonProps) {
  const jsonString = JSON.stringify(architecture, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    toast.success("Canonical JSON copied to clipboard");
  };

  const handleDownload = () => {
    downloadFile(
      jsonString,
      `${architecture.title.toLowerCase().replace(/\s+/g, "-")}.json`,
      "application/json"
    );
    toast.success("Canonical JSON downloaded");
  };

  return (
    <Card className="p-4 bg-background border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Canonical Architecture JSON</h3>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleCopy}
          >
            <Copy className="w-4 h-4" />
            Copy
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleDownload}
          >
            <Download className="w-4 h-4" />
            Download
          </Button>
        </div>
      </div>

      <pre className="bg-card/50 p-4 rounded overflow-auto max-h-96 text-xs font-mono text-muted-foreground">
        {jsonString}
      </pre>
    </Card>
  );
}

