import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Children, isValidElement, ReactNode } from "react";
import ArchitectureDiagram from "./ArchitectureDiagram";
import { FileText } from "lucide-react";

interface ArchitectureReportProps {
  markdown: string;
}

export default function ArchitectureReport({ markdown }: ArchitectureReportProps) {
  const report = typeof markdown === "string" ? markdown.trim() : "";

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center p-12 dark:bg-black/40 bg-white/40 backdrop-blur-md rounded-2xl border dark:border-white/5 border-black/5 dark:text-slate-400 text-slate-600">
        <FileText className="w-12 h-12 mb-4 opacity-50" />
        <p>No architecture report was generated.</p>
      </div>
    );
  }

  return (
    <div className="dark:bg-black/40 bg-white/40 backdrop-blur-md rounded-2xl border dark:border-white/5 border-black/5 p-6 md:p-10 lg:p-14 mb-8 shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="max-w-4xl mx-auto relative z-10">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }: { children?: ReactNode }) => (
              <div className="flex items-center gap-4 mt-2 mb-10 pb-4 border-b dark:border-white/10 border-black/10">
                <span className="w-1.5 h-8 bg-gradient-to-b from-primary to-primary/30 rounded-full shadow-[0_0_15px_rgba(var(--primary),0.5)]" />
                <h1 className="text-3xl md:text-4xl font-extrabold bg-gradient-to-br dark:from-white dark:to-white/60 from-slate-900 to-slate-600 bg-clip-text text-transparent tracking-tight">
                  {children}
                </h1>
              </div>
            ),
            h2: ({ children }: { children?: ReactNode }) => (
              <div className="flex items-center gap-3 mt-12 mb-6 group">
                <span className="w-1 h-6 bg-primary/70 rounded-full group-hover:bg-primary group-hover:shadow-[0_0_10px_rgba(var(--primary),0.5)] transition-all" />
                <h2 className="text-xl md:text-2xl font-bold dark:text-slate-100 text-slate-900 tracking-tight">
                  {children}
                </h2>
              </div>
            ),
            h3: ({ children }: { children?: ReactNode }) => (
              <div className="flex items-center gap-2 mt-8 mb-4">
                <span className="w-1.5 h-1.5 bg-primary/50 rounded-full" />
                <h3 className="text-lg font-semibold dark:text-slate-200 text-slate-800">
                  {children}
                </h3>
              </div>
            ),
            p: ({ children }: { children?: ReactNode }) => (
              <p className="text-[15px] dark:text-slate-300/90 text-slate-700/90 leading-relaxed mb-6 font-medium">
                {children}
              </p>
            ),
            ul: ({ children }: { children?: ReactNode }) => (
              <ul className="space-y-3 mb-8 text-[15px] dark:text-slate-300/90 text-slate-700/90 font-medium">
                {children}
              </ul>
            ),
            ol: ({ children }: { children?: ReactNode }) => (
              <ol className="mb-8 list-decimal list-outside ml-5 space-y-3 text-[15px] dark:text-slate-300/90 text-slate-700/90 font-medium marker:text-primary/70">
                {children}
              </ol>
            ),
            li: ({ children }: { children?: ReactNode }) => (
              <li className="flex items-start gap-3 leading-relaxed">
                <span className="mt-[7px] shrink-0 w-1.5 h-1.5 rounded-full bg-primary/60 shadow-[0_0_8px_rgba(var(--primary),0.4)]" />
                <span className="flex-1">{children}</span>
              </li>
            ),
            blockquote: ({ children }: { children?: ReactNode }) => (
              <blockquote className="relative my-8 px-6 py-4 rounded-r-2xl bg-gradient-to-r from-primary/10 to-transparent border-l-2 border-primary/70 dark:text-slate-300 text-slate-700 italic text-[15px]">
                {children}
              </blockquote>
            ),
            strong: ({ children }: { children?: ReactNode }) => (
              <strong className="font-bold dark:text-slate-100 text-slate-900 dark:bg-white/5 bg-black/5 px-1 rounded">
                {children}
              </strong>
            ),
            code: ({ children, className }: { children?: ReactNode; className?: string }) => (
              <code className={`${className || ""} rounded-md dark:bg-black/40 bg-white/60 border dark:border-white/10 border-black/10 px-1.5 py-0.5 font-mono text-[13px] dark:text-primary/90 text-primary font-semibold shadow-inner`}>
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
                  <div className="my-10 rounded-2xl overflow-hidden border dark:border-white/5 border-black/5 shadow-2xl">
                    <ArchitectureDiagram
                      title="Architecture Diagram"
                      diagram={String(child.props.children || "")}
                    />
                  </div>
                );
              }

              return (
                <div className="relative group my-8">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                  <pre className="overflow-x-auto rounded-xl border dark:border-white/10 border-black/10 dark:bg-[#0d1117]/80 bg-slate-50/80 backdrop-blur-md p-5 font-mono text-[13px] leading-relaxed dark:text-slate-300 text-slate-700 shadow-xl workspace-scrollbar relative z-10">
                    {children}
                  </pre>
                </div>
              );
            },
            table: ({ children }: { children?: ReactNode }) => (
              <div className="overflow-x-auto rounded-2xl border dark:border-white/10 border-black/10 my-8 shadow-xl dark:bg-black/20 bg-white/40 backdrop-blur-sm">
                <table className="w-full border-collapse text-left text-[14px]">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }: { children?: ReactNode }) => (
              <th className="border-b dark:border-white/10 border-black/10 px-5 py-4 font-semibold dark:text-slate-200 text-slate-800 dark:bg-white/5 bg-black/5 uppercase tracking-wider text-[11px]">
                {children}
              </th>
            ),
            td: ({ children }: { children?: ReactNode }) => (
              <td className="border-b dark:border-white/5 border-black/5 px-5 py-4 dark:text-slate-300/90 text-slate-700/90 font-medium">
                {children}
              </td>
            ),
            hr: () => <hr className="my-12 border-t dark:border-white/10 border-black/10 dark:shadow-[0_1px_0_rgba(255,255,255,0.02)] shadow-[0_1px_0_rgba(0,0,0,0.02)]" />,
          }}
        >
          {report}
        </ReactMarkdown>
      </div>
    </div>
  );
}
