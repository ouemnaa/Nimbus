import { ArchitectureComponent } from "@/types/architecture";
import { Cloud, Database, Lock, Eye, Network, Zap, Server } from "lucide-react";

interface ArchitectureComponentsProps {
  components: ArchitectureComponent[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  Networking: <Network className="w-5 h-5" />,
  Compute: <Zap className="w-5 h-5" />,
  "Load balancing": <Cloud className="w-5 h-5" />,
  Database: <Database className="w-5 h-5" />,
  Security: <Lock className="w-5 h-5" />,
  Observability: <Eye className="w-5 h-5" />,
};

const categoryColors: Record<string, string> = {
  Networking: "from-blue-500/20 to-cyan-500/5 text-cyan-400 border-cyan-500/30",
  Compute: "from-amber-500/20 to-orange-500/5 text-amber-400 border-amber-500/30",
  "Load balancing": "from-sky-500/20 to-blue-500/5 text-sky-400 border-sky-500/30",
  Database: "from-emerald-500/20 to-green-500/5 text-emerald-400 border-emerald-500/30",
  Security: "from-red-500/20 to-rose-500/5 text-red-400 border-red-500/30",
  Observability: "from-purple-500/20 to-fuchsia-500/5 text-purple-400 border-purple-500/30",
};

export default function ArchitectureComponents({ components }: ArchitectureComponentsProps) {
  const groupedByCategory = components.reduce(
    (acc, component) => {
      if (!acc[component.category]) {
        acc[component.category] = [];
      }
      acc[component.category].push(component);
      return acc;
    },
    {} as Record<string, ArchitectureComponent[]>
  );

  return (
    <div className="space-y-12 pb-8">
      {Object.entries(groupedByCategory).map(([category, items]) => {
        const theme = categoryColors[category] || "from-slate-500/20 to-slate-500/5 text-slate-400 border-slate-500/30";
        return (
          <div key={category} className="space-y-6">
            <div className="flex items-center gap-3 pb-3 border-b dark:border-white/5 border-black/5">
              <div className={`p-2 rounded-xl bg-gradient-to-br ${theme.split(' ')[0]} ${theme.split(' ')[1]} border ${theme.split(' ')[3]} shadow-lg`}>
                {categoryIcons[category] || <Server className="h-5 w-5" />}
              </div>
              <div>
                <h3 className="text-lg font-bold dark:text-slate-100 text-slate-900 tracking-wide uppercase">
                  {category.replace(/_/g, " ")}
                </h3>
                <p className="text-xs font-mono text-muted-foreground">{items.length} COMPONENT{items.length !== 1 ? 'S' : ''}</p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
              {items.map((component) => (
                <div 
                  key={component.id} 
                  className="group relative overflow-hidden rounded-2xl dark:bg-black/40 bg-white/40 backdrop-blur-md border dark:border-white/5 border-black/5 dark:hover:border-white/20 hover:border-black/20 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1"
                >
                  {/* Subtle top glow line */}
                  <div className={`absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r ${theme.split(' ')[0]} to-transparent opacity-50 group-hover:opacity-100 transition-opacity`} />
                  
                  <div className="p-5 flex flex-col h-full justify-between">
                    <div className="space-y-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h4 className="font-bold text-base dark:text-slate-100 text-slate-900 leading-tight truncate">
                            {component.name}
                          </h4>
                          <p className={`text-[10px] font-bold mt-1.5 uppercase tracking-widest font-mono truncate ${theme.split(' ')[2]}`}>
                            {component.provider_type || component.type || "Cloud resource"}
                          </p>
                        </div>
                        <span
                          className={`text-[9px] font-bold px-2.5 py-1 rounded-full border shrink-0 uppercase tracking-widest ${
                            component.scope.toLowerCase().includes("public") || component.scope.toLowerCase().includes("global")
                              ? "dark:bg-amber-500/10 bg-amber-500/20 dark:text-amber-400 text-amber-700 dark:border-amber-500/20 border-amber-500/30"
                              : "dark:bg-emerald-500/10 bg-emerald-500/20 dark:text-emerald-400 text-emerald-700 dark:border-emerald-500/20 border-emerald-500/30"
                          }`}
                        >
                          {component.scope.replace(/_/g, " ").toLowerCase()}
                        </span>
                      </div>
                      <p className="text-sm dark:text-slate-400 text-slate-600 leading-relaxed">
                        {component.purpose}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
