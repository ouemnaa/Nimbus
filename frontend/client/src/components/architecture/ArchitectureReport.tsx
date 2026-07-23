import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "@/components/ui/card";
import { ReactNode } from "react";

interface ArchitectureReportProps {
  markdown: string;
}

export default function ArchitectureReport({ markdown }: ArchitectureReportProps) {
  return (
    <Card className="p-6 bg-background border-border prose prose-invert max-w-none">
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
          li: ({ children }: { children?: ReactNode }) => <li className="ml-2">{children}</li>,
          code: ({ children }: { children?: ReactNode }) => (
            <code className="bg-card px-2 py-1 rounded text-xs font-mono text-accent">
              {children}
            </code>
          ),
          pre: ({ children }: { children?: ReactNode }) => (
            <pre className="bg-card/50 p-4 rounded overflow-auto mb-3 text-xs">{children}</pre>
          ),
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
        }}
      >
        {markdown}
      </ReactMarkdown>
    </Card>
  );
}
