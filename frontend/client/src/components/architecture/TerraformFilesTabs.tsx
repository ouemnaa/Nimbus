import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import type { TerraformGeneration } from "@/types/architecture";
import { Copy, FileCode, FolderClosed, Terminal } from "lucide-react";
import { toast } from "sonner";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

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
    <div className="flex flex-col overflow-hidden rounded-md border border-border/50 bg-[#090d13] shadow-none">
      <div className="flex items-center justify-between border-b border-border/50 bg-[#0c1017] px-4 py-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            Terraform Workspace
          </p>
          <p className="text-xs text-muted-foreground">
            {generation.status} · {files.length} files
          </p>
        </div>
      </div>

      <div className="flex h-[600px] w-full">
        {/* Sidebar File Explorer */}
        <div className="flex w-64 flex-col border-r border-border/50 bg-[#0c1017]">
          <div className="flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <FolderClosed className="size-4" />
            Explorer
          </div>
          <div className="flex-1 overflow-y-auto py-2">
            {files.map((file) => (
              <button
                key={file.path}
                onClick={() => setActivePath(file.path)}
                className={`flex w-full items-center gap-2 px-4 py-1.5 text-left text-sm transition-colors hover:bg-white/5 ${
                  activePath === file.path
                    ? "bg-white/10 font-medium text-blue-400"
                    : "text-slate-400"
                }`}
              >
                <FileCode className="size-4 shrink-0" />
                <span className="truncate">{file.path}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Main Editor Area */}
        <div className="flex flex-1 flex-col min-w-0 bg-[#1e1e1e]">
          <div className="flex items-center justify-between border-b border-border/50 bg-[#181818] px-4 py-2">
            <div className="flex items-center gap-2 text-sm font-mono text-slate-300">
              <FileCode className="size-4 text-blue-400" />
              {activePath}
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="h-7 gap-2 bg-white/10 hover:bg-white/20 text-xs border-0"
              onClick={copyActiveFile}
            >
              <Copy className="size-3" />
              Copy
            </Button>
          </div>
          <div className="flex-1 overflow-auto workspace-scrollbar">
            <SyntaxHighlighter
              language="hcl"
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                padding: "1rem",
                background: "transparent",
                fontSize: "13px",
              }}
              showLineNumbers
            >
              {activeFile.content}
            </SyntaxHighlighter>
          </div>
        </div>
      </div>

      {/* Warnings & Next Steps Terminal-like View */}
      {(generation.warnings.length > 0 || generation.nextSteps.length > 0) && (
        <div className="border-t border-border/50 bg-[#0c1017] p-0">
          <div className="flex items-center gap-2 border-b border-border/50 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Terminal className="size-4" />
            Output
          </div>
          <div className="grid gap-6 p-4 md:grid-cols-2 max-h-64 overflow-y-auto">
            {generation.warnings.length > 0 && (
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-amber-400 flex items-center gap-2">
                  <span className="size-2 rounded-full bg-amber-400"></span>
                  Warnings
                </p>
                <ul className="space-y-2 text-xs text-slate-300 font-mono">
                  {generation.warnings.map((warning, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-amber-500/50">⚠</span>
                      <span className="leading-relaxed">{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {generation.nextSteps.length > 0 && (
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-blue-400 flex items-center gap-2">
                  <span className="size-2 rounded-full bg-blue-400"></span>
                  Next steps
                </p>
                <ul className="space-y-2 text-xs text-slate-300 font-mono">
                  {generation.nextSteps.map((step, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-blue-500/50">→</span>
                      <span className="leading-relaxed">{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
