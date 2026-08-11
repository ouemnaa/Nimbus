import { useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import type { TerraformGeneration } from "@/types/architecture";
import { Copy } from "lucide-react";
import { toast } from "sonner";

interface TerraformFilesTabsProps {
  generation: TerraformGeneration;
}

export default function TerraformFilesTabs({
  generation,
}: TerraformFilesTabsProps) {
  const files = generation.files;
  const [activePath, setActivePath] = useState(files[0]?.path || "");
  const activeFile = useMemo(
    () => files.find((file) => file.path === activePath) || files[0],
    [activePath, files]
  );

  if (!files.length) {
    return (
      <div className="rounded-md border border-border/50 bg-bg-surface-soft p-4 text-sm text-muted-foreground">
        No Terraform files were returned.
      </div>
    );
  }

  const copyActiveFile = () => {
    if (!activeFile) {
      return;
    }
    navigator.clipboard.writeText(activeFile.content);
    toast.success(`${activeFile.path} copied`);
  };

  return (
    <div className="overflow-hidden rounded-md border border-border/50 bg-[#090d13] shadow-none">
      <div className="flex items-center justify-between border-b border-border/50 px-3 py-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            Terraform files
          </p>
          <p className="text-xs text-muted-foreground">
            {generation.status} · {files.length} files
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={copyActiveFile}>
          <Copy className="size-4" />
          Copy file
        </Button>
      </div>

      <Tabs value={activePath} onValueChange={setActivePath}>
        <TabsList className="workspace-tabs-list h-auto w-full justify-start overflow-x-auto rounded-none border-b border-border/40 bg-bg-surface-soft p-0">
          {files.map((file) => (
            <TabsTrigger
              key={file.path}
              value={file.path}
              className="workspace-tab max-w-[220px] shrink-0"
              title={file.path}
            >
              {file.path}
            </TabsTrigger>
          ))}
        </TabsList>

        {files.map((file) => (
          <TabsContent key={file.path} value={file.path} className="m-0">
            <pre className="workspace-scrollbar max-h-[620px] overflow-auto p-4 text-xs leading-relaxed text-slate-100">
              <code>{file.content}</code>
            </pre>
          </TabsContent>
        ))}
      </Tabs>

      {(generation.warnings.length > 0 || generation.nextSteps.length > 0) && (
        <div className="grid gap-4 border-t border-border/50 p-4 md:grid-cols-2">
          {generation.warnings.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-300">
                Warnings
              </p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                {generation.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {generation.nextSteps.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary">
                Next steps
              </p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                {generation.nextSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
