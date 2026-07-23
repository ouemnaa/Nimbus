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
      <Card className="border-border bg-background p-6 text-sm text-muted-foreground">
        No Markdown report was returned.
      </Card>
    );
  }

  return (
    <Card className="max-w-none border-border bg-background p-6 text-foreground">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }: { children?: ReactNode }) => (
            <h1 className="text-2xl font-bold text-foreground mt-6 mb-4">{children}</h1>
          ),
          h2: ({ children }: { children?: ReactNode }) => (
            <h2 className="text-xl font-semibold text-foreground mt-5 mb-3">{children}</h2>
          ),
          h3: ({ children }: { children?: ReactNode }) => (
            <h3 className="text-lg font-semibold text-foreground mt-4 mb-2">{children}</h3>
          ),
          p: ({ children }: { children?: ReactNode }) => (
            <p className="text-sm text-muted-foreground leading-relaxed mb-3">{children}</p>
          ),
          ul: ({ children }: { children?: ReactNode }) => (
            <ul className="list-disc list-inside space-y-1 mb-3 text-sm text-muted-foreground">
              {children}
            </ul>
          ),
          ol: ({ children }: { children?: ReactNode }) => (
            <ol className="mb-3 list-inside list-decimal space-y-1 text-sm text-muted-foreground">
              {children}
            </ol>
          ),
          li: ({ children }: { children?: ReactNode }) => <li className="ml-2">{children}</li>,
          strong: ({ children }: { children?: ReactNode }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          code: ({ children, className }: { children?: ReactNode; className?: string }) => (
            <code className={`${className || ""} rounded bg-card px-2 py-1 font-mono text-xs text-gold-cloud`}>
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
                <div className="my-5">
                  <ArchitectureDiagram
                    title="Architecture Diagram"
                    diagram={String(child.props.children || "")}
                  />
                </div>
              );
            }

            return (
              <pre className="mb-3 overflow-auto rounded bg-card/50 p-4 text-xs text-foreground">
                {children}
              </pre>
            );
          },
          table: ({ children }: { children?: ReactNode }) => (
            <table className="w-full border-collapse mb-3 text-sm">{children}</table>
          ),
          th: ({ children }: { children?: ReactNode }) => (
            <th className="border border-border px-3 py-2 text-left font-semibold text-foreground bg-card/50">
              {children}
            </th>
          ),
          td: ({ children }: { children?: ReactNode }) => (
            <td className="border border-border px-3 py-2 text-muted-foreground">{children}</td>
          ),
          hr: () => <hr className="my-6 border-border" />,
        }}
      >
        {report}
      </ReactMarkdown>
    </Card>
  );
}
