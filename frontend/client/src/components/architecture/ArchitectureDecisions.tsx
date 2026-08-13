import { useState, useEffect } from "react";
import { ArchitectureDecision } from "@/types/architecture";
import { ChevronRight, CheckCircle2, XCircle, Info, SplitSquareHorizontal } from "lucide-react";

interface ArchitectureDecisionsProps {
  decisions: ArchitectureDecision[];
}

export default function ArchitectureDecisions({ decisions }: ArchitectureDecisionsProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    if (decisions.length > 0 && !activeId) {
      setActiveId(decisions[0].id || `decision-0`);
    }
  }, [decisions, activeId]);

  const activeDecision = decisions.find(
    (d, i) => (d.id || `decision-${i}`) === activeId
  ) || decisions[0];

  const alternatives =
    activeDecision?.alternatives ||
    activeDecision?.alternatives_considered?.map((alternative) => ({
      name: alternative.option,
      pros: alternative.advantages,
      cons: alternative.disadvantages,
      reason_not_selected: alternative.reason_not_selected,
    })) ||
    [];

  if (!decisions.length) {
    return <div className="p-8 text-center text-muted-foreground">No architecture decisions were recorded.</div>;
  }

  return (
    <div className="flex flex-col md:flex-row gap-6 min-h-[600px] pb-8">
      {/* Left Sidebar - List of Decisions */}
      <div className="md:w-1/3 flex flex-col gap-3 h-[600px] overflow-y-auto pr-2 workspace-scrollbar">
        <div className="flex items-center gap-2 mb-2 px-1">
          <SplitSquareHorizontal className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wider dark:text-slate-300 text-slate-700">Decision Log</h3>
        </div>
        
        {decisions.map((decision, index) => {
          const id = decision.id || `decision-${index}`;
          const isActive = activeId === id;
          
          return (
            <button
              key={id}
              onClick={() => setActiveId(id)}
              className={`group flex items-center justify-between text-left p-4 rounded-xl transition-all duration-300 border ${
                isActive 
                  ? "dark:bg-white/10 bg-black/10 dark:border-white/20 border-black/20 shadow-lg" 
                  : "dark:bg-black/20 bg-white/40 border-transparent dark:hover:bg-white/5 hover:bg-black/5 dark:hover:border-white/10 hover:border-black/10"
              }`}
            >
              <div className="flex flex-col gap-1 pr-4">
                <span className={`text-sm font-semibold transition-colors ${isActive ? "text-primary" : "dark:text-slate-300 text-slate-700 dark:group-hover:text-slate-100 group-hover:text-slate-900"}`}>
                  {decision.title}
                </span>
                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">
                  Decision #{index + 1}
                </span>
              </div>
              <ChevronRight className={`w-4 h-4 shrink-0 transition-transform ${isActive ? "text-primary translate-x-1" : "dark:text-slate-600 text-slate-400 dark:group-hover:text-slate-400 group-hover:text-slate-600"}`} />
            </button>
          );
        })}
      </div>

      {/* Right Panel - Decision Details */}
      <div className="md:w-2/3 h-[600px] overflow-y-auto workspace-scrollbar">
        {activeDecision && (
          <div className="dark:bg-black/40 bg-white/40 backdrop-blur-md rounded-2xl border dark:border-white/10 border-black/10 p-6 sm:p-8 relative overflow-hidden h-full">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 to-transparent" />
            
            <div className="mb-8">
              <h2 className="text-2xl font-bold dark:text-slate-100 text-slate-900 mb-4">{activeDecision.title}</h2>
              <div className="bg-primary/5 border border-primary/20 rounded-xl p-5">
                <h4 className="text-xs font-semibold text-primary uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Info className="w-4 h-4" />
                  Rationale
                </h4>
                <p className="text-sm dark:text-slate-200 text-slate-800 leading-relaxed">
                  {activeDecision.rationale}
                </p>
              </div>
            </div>

            {alternatives.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold dark:text-slate-400 text-slate-600 uppercase tracking-widest mb-4">
                  Alternatives Considered
                </h4>
                <div className="space-y-4">
                  {alternatives.map((alt, idx) => (
                    <div key={idx} className="dark:bg-black/20 bg-white/60 border dark:border-white/5 border-black/5 rounded-xl p-5 dark:hover:border-white/10 hover:border-black/10 transition-colors">
                      <div className="flex items-center gap-3 mb-4 pb-3 border-b dark:border-white/5 border-black/5">
                        <div className="w-8 h-8 rounded-full dark:bg-slate-800 bg-slate-200 flex items-center justify-center shrink-0 border dark:border-slate-700 border-slate-300">
                          <span className="text-xs font-bold dark:text-slate-400 text-slate-600">{idx + 1}</span>
                        </div>
                        <h5 className="font-semibold text-sm dark:text-slate-200 text-slate-800">{alt.name}</h5>
                      </div>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                        <div className="dark:bg-emerald-500/5 bg-emerald-50 rounded-lg p-3 border dark:border-emerald-500/10 border-emerald-200">
                          <h6 className="text-[10px] uppercase font-bold tracking-widest text-emerald-500 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
                            <CheckCircle2 className="w-3 h-3" /> Pros
                          </h6>
                          <ul className="space-y-1">
                            {alt.pros.map((pro, i) => (
                              <li key={i} className="text-xs dark:text-emerald-100/70 text-emerald-900/70 leading-relaxed">• {pro}</li>
                            ))}
                          </ul>
                        </div>
                        
                        <div className="dark:bg-red-500/5 bg-red-50 rounded-lg p-3 border dark:border-red-500/10 border-red-200">
                          <h6 className="text-[10px] uppercase font-bold tracking-widest text-red-500 dark:text-red-400 mb-2 flex items-center gap-1.5">
                            <XCircle className="w-3 h-3" /> Cons
                          </h6>
                          <ul className="space-y-1">
                            {alt.cons.map((con, i) => (
                              <li key={i} className="text-xs dark:text-red-100/70 text-red-900/70 leading-relaxed">• {con}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                      
                      {alt.reason_not_selected && (
                        <div className="dark:bg-white/5 bg-black/5 rounded-lg p-3 text-xs dark:text-slate-300 text-slate-700 leading-relaxed border dark:border-white/5 border-black/5">
                          <span className="font-semibold dark:text-slate-400 text-slate-600 mr-2">Why not selected:</span>
                          {alt.reason_not_selected}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
