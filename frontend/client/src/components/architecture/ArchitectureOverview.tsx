import { CanonicalArchitecture } from "@/types/architecture";
import {
  ShieldCheck,
  Banknote,
  Settings,
  Scaling,
  Target,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  Info
} from "lucide-react";

interface ArchitectureOverviewProps {
  architecture: CanonicalArchitecture;
}

export default function ArchitectureOverview({ architecture }: ArchitectureOverviewProps) {
  const solutionSummary =
    typeof architecture.solution === "string"
      ? architecture.solution
      : architecture.solution.summary;

  const getAssessmentIcon = (label: string) => {
    switch (label) {
      case "Security":
        return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      case "Cost Efficiency":
        return <Banknote className="w-5 h-5 text-amber-400" />;
      case "Operational Complexity":
        return <Settings className="w-5 h-5 text-blue-400" />;
      case "Scalability":
        return <Scaling className="w-5 h-5 text-purple-400" />;
      default:
        return <Target className="w-5 h-5 text-primary" />;
    }
  };

  const getAssessmentColor = (value: string) => {
    const val = value.toLowerCase();
    if (val.includes("high") || val.includes("strong") || val.includes("good")) return "text-emerald-300";
    if (val.includes("medium") || val.includes("moderate")) return "text-amber-300";
    return "text-red-300";
  };

  const assessments = [
    { label: "Security", value: "Strong" },
    { label: "Cost Efficiency", value: "High" },
    { label: "Operational Complexity", value: "Low–Medium" },
    { label: "Scalability", value: "Good" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 auto-rows-min pb-8">
      
      {/* Hero Summary - Spans full width on small, 8 cols on large */}
      <div className="md:col-span-8 group relative overflow-hidden rounded-2xl dark:border-white/10 border-black/10 dark:bg-black/40 bg-white/40 backdrop-blur-md p-6 shadow-2xl transition-all duration-300 dark:hover:border-white/20 hover:border-black/20 hover:shadow-primary/5">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent opacity-50" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-4">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <h3 className="text-lg font-semibold bg-gradient-to-r dark:from-white dark:to-white/70 from-slate-900 to-slate-600 bg-clip-text text-transparent">
              Architecture Summary
            </h3>
          </div>
          <p className="text-sm dark:text-slate-300 text-slate-700 leading-relaxed font-medium">
            {solutionSummary || "No solution summary was returned."}
          </p>
        </div>
      </div>

      {/* Assessment Metrics - Bento Grid within */}
      <div className="md:col-span-4 grid grid-cols-2 gap-3">
        {assessments.map(({ label, value }) => (
          <div
            key={label}
            className="flex flex-col justify-center rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-4 transition-all dark:hover:bg-white/5 hover:bg-black/5 hover:-translate-y-1"
          >
            <div className="flex items-center gap-2 mb-2">
              {getAssessmentIcon(label)}
            </div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
              {label}
            </p>
            <p className={`text-sm font-bold mt-1 ${getAssessmentColor(value)}`}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Architecture Qualities */}
      <div className="md:col-span-4 rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
        <h3 className="text-sm font-semibold dark:text-slate-200 text-slate-800 mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-primary" />
          Key Qualities
        </h3>
        <ul className="space-y-3">
          {[
            "Managed compute",
            "Private database",
            "Low operational overhead",
            "Secure secret handling",
          ].map((quality, i) => (
            <li key={i} className="text-xs dark:text-slate-300 text-slate-700 flex items-start gap-3 group">
              <span className="mt-1 w-1 h-1 rounded-full bg-primary/50 group-hover:bg-primary transition-colors" />
              <span className="leading-relaxed">{quality}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Considerations */}
      <div className="md:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
          <h3 className="mb-4 text-sm font-semibold dark:text-slate-200 text-slate-800 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Security Considerations
          </h3>
          {architecture.security_considerations.length ? (
            <ul className="space-y-3">
              {architecture.security_considerations.map((item, index) => (
                <li key={index} className="text-xs dark:text-slate-300 text-slate-700 flex items-start gap-3">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-sm bg-emerald-500/50" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">No security considerations.</p>
          )}
        </div>

        <div className="rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
          <h3 className="mb-4 text-sm font-semibold dark:text-slate-200 text-slate-800 flex items-center gap-2">
            <Banknote className="w-4 h-4 text-amber-400" />
            Cost Considerations
          </h3>
          {architecture.cost_considerations.length ? (
            <ul className="space-y-3">
              {architecture.cost_considerations.map((item, index) => (
                <li key={index} className="text-xs dark:text-slate-300 text-slate-700 flex items-start gap-3">
                  <span className="mt-1 shrink-0 w-1.5 h-1.5 rounded-sm bg-amber-500/50" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">No cost considerations.</p>
          )}
        </div>
      </div>

      {/* Open Questions & Assumptions */}
      <div className="md:col-span-6 rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
        <h3 className="text-sm font-semibold dark:text-slate-200 text-slate-800 mb-4 flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-400" />
          Assumptions
        </h3>
        <ul className="space-y-3">
          {architecture.assumptions.map((assumption, idx) => (
            <li key={idx} className="text-xs dark:text-slate-300 text-slate-700 flex items-start gap-3 dark:bg-white/5 bg-black/5 p-2 rounded-lg dark:border-white/5 border-black/5">
              <span className="leading-relaxed">{assumption}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="md:col-span-6 rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
        <h3 className="text-sm font-semibold dark:text-slate-200 text-slate-800 mb-4 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-yellow-400" />
          Open Questions
        </h3>
        {architecture.open_questions.length ? (
          <ul className="space-y-3">
            {architecture.open_questions.map((question, idx) => (
              <li key={idx} className="text-xs dark:text-slate-300 text-slate-700 flex items-start gap-3 dark:bg-white/5 bg-black/5 p-2 rounded-lg dark:border-white/5 border-black/5">
                <span className="leading-relaxed">{question}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">No open questions.</p>
        )}
      </div>

      {/* Risks */}
      <div className="md:col-span-12 rounded-2xl dark:border-white/5 border-black/5 dark:bg-black/40 bg-white/40 backdrop-blur-md p-5 transition-all dark:hover:bg-white/5 hover:bg-black/5">
        <h3 className="text-sm font-semibold dark:text-slate-200 text-slate-800 mb-4 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          Risks & Mitigations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {architecture.risks.map((risk, idx) => (
            <div key={idx} className="group relative dark:bg-black/20 bg-white/60 rounded-xl p-4 border dark:border-white/5 border-black/5 dark:hover:border-red-500/30 hover:border-red-500/30 transition-colors">
              <div className="absolute top-0 left-0 w-1 h-full bg-red-500/20 rounded-l-xl group-hover:bg-red-500/50 transition-colors" />
              <p className="text-sm font-semibold dark:text-slate-200 text-slate-800 ml-2">
                {risk.title || risk.risk || "Architecture risk"}
              </p>
              {risk.description && (
                <p className="mt-2 text-xs dark:text-slate-400 text-slate-600 ml-2 leading-relaxed">
                  {risk.description}
                </p>
              )}
              <div className="mt-3 ml-2 flex gap-2 items-start dark:bg-emerald-500/10 bg-emerald-50 text-emerald-700 dark:text-emerald-200/90 p-2 rounded-md border dark:border-emerald-500/20 border-emerald-500/30 text-xs">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{risk.mitigation}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
