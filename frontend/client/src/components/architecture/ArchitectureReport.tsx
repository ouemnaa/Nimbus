import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "@/components/ui/card";
import { Children, isValidElement, ReactNode } from "react";
import ArchitectureDiagram from "./ArchitectureDiagram";

interface ArchitectureReportProps {
  markdown: string;
}

export default function ArchitectureReport({ markdown }: ArchitectureReportProps) {
  const report = typeof markdown === "string" ? markdown.trim() : "";

  if (!report) {
    return (
      <Card className="border-border/40 bg-card p-8 text-sm text-text-muted rounded-2xl shadow-sm">
        No Markdown report was returned.
      </Card>
    );
  }

  return (
    <Card className="max-w-none border-border/40 bg-card p-8 text-text-primary rounded-2xl shadow-sm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }: { children?: ReactNode }) => (
            <div className="flex items-center gap-3 mt-8 mb-6 pb-2 border-b border-border/30">
              <span className="w-1.5 h-6 bg-gradient-to-b from-primary to-deep-ochre rounded-full" />
              <h1 className="text-2xl font-bold text-text-primary tracking-tight">{children}</h1>
            </div>
          ),
          h2: ({ children }: { children?: ReactNode }) => (
            <div className="flex items-center gap-2 mt-6 mb-4">
              <span className="w-1.5 h-4 bg-primary/70 rounded-full" />
              <h2 className="text-lg font-semibold text-text-primary tracking-tight">{children}</h2>
            </div>
          ),
          h3: ({ children }: { children?: ReactNode }) => (
            <div className="flex items-center gap-2 mt-5 mb-3">
              <span className="w-1 h-3 bg-primary/50 rounded-full" />
              <h3 className="text-base font-semibold text-text-primary">{children}</h3>
            </div>
          ),
          p: ({ children }: { children?: ReactNode }) => (
            <p className="text-sm text-text-secondary leading-relaxed mb-4">{children}</p>
          ),
          ul: ({ children }: { children?: ReactNode }) => (
            <ul className="space-y-2 mb-4 text-sm text-text-secondary pl-1">
              {children}
            </ul>
          ),
          ol: ({ children }: { children?: ReactNode }) => (
            <ol className="mb-4 list-decimal list-inside space-y-2 text-sm text-text-secondary pl-1">
              {children}
            </ol>
          ),
          li: ({ children }: { children?: ReactNode }) => (
            <li className="flex items-start gap-2.5 text-sm text-text-secondary leading-relaxed">
              <span className="mt-2 flex h-1.5 w-1.5 shrink-0 rounded-full bg-primary/80" />
              <span className="flex-1">{children}</span>
            </li>
          ),
          blockquote: ({ children }: { children?: ReactNode }) => (
            <blockquote className="border-l-4 border-primary bg-bg-surface-soft/60 px-4 py-3 my-4 rounded-r-lg italic text-text-secondary">
              {children}
            </blockquote>
          ),
          strong: ({ children }: { children?: ReactNode }) => (
            <strong className="font-semibold text-text-primary">{children}</strong>
          ),
          code: ({ children, className }: { children?: ReactNode; className?: string }) => (
            <code className={`${className || ""} rounded bg-bg-surface-soft px-1.5 py-0.5 font-mono text-xs text-primary font-medium`}>
              {children}
            </code>
          ),
          pre: ({ children }: { children?: ReactNode }) => {
            const child = Children.toArray(children)[0];
            if (
              isValidElement<{ className?: string; children?: ReactNode }>(child) &&
              child.props.className?.includes("language-mermaid")
            ) {
              return (
                <div className="my-6">
                  <ArchitectureDiagram
                    title="Architecture Diagram"
                    diagram={String(child.props.children || "")}
                  />
                </div>
              );
            }

            return (
              <pre className="mb-4 overflow-auto rounded-xl border border-border/40 bg-bg-deep p-4 font-mono text-xs text-text-primary shadow-xs">
                {children}
              </pre>
            );
          },
          table: ({ children }: { children?: ReactNode }) => (
            <div className="overflow-hidden rounded-xl border border-border/40 my-6 shadow-xs">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }: { children?: ReactNode }) => (
            <th className="border-b border-border/40 px-4 py-3 text-left font-semibold text-text-primary bg-bg-surface-soft">
              {children}
            </th>
          ),
          td: ({ children }: { children?: ReactNode }) => (
            <td className="border-b border-border/20 px-4 py-3 text-text-secondary bg-card/40">{children}</td>
          ),
          hr: () => <hr className="my-8 border-border/30" />,
        }}
      >
        {report}
      </ReactMarkdown>
    </Card>
  );
}
