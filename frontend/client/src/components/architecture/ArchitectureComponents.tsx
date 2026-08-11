import { Card } from "@/components/ui/card";
import { ArchitectureComponent } from "@/types/architecture";
import { Cloud, Database, Lock, Eye, Network, Zap } from "lucide-react";

interface ArchitectureComponentsProps {
  components: ArchitectureComponent[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  Networking: <Network className="w-4 h-4" />,
  Compute: <Zap className="w-4 h-4" />,
  "Load balancing": <Cloud className="w-4 h-4" />,
  Database: <Database className="w-4 h-4" />,
  Security: <Lock className="w-4 h-4" />,
  Observability: <Eye className="w-4 h-4" />,
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
    <div className="space-y-8">
      {Object.entries(groupedByCategory).map(([category, items]) => (
        <div key={category} className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-border/20">
            <div className="p-1 rounded-md bg-primary/10 text-primary">
              {categoryIcons[category] || <Cloud className="h-4 w-4" />}
            </div>
            <h3 className="text-sm font-semibold text-text-primary tracking-wide uppercase">
              {category.replace(/_/g, " ")}
            </h3>
            <span className="text-xs text-text-muted">({items.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((component) => (
              <Card key={component.id} className="p-5 bg-card border border-border/40 shadow-sm hover:shadow-md hover:border-gold-soft/50 transition-all duration-300 rounded-xl flex flex-col justify-between min-h-[140px]">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h4 className="font-semibold text-sm text-text-primary leading-tight truncate">{component.name}</h4>
                      <p className="text-[10px] font-medium text-text-muted mt-1 uppercase tracking-wider font-mono truncate">
                        {component.provider_type || component.type || "Cloud resource"}
                      </p>
                    </div>
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded-full border shrink-0 ${
                        component.scope.toLowerCase().includes("public") || component.scope.toLowerCase().includes("global")
                          ? "bg-amber-500/10 text-amber-700 dark:text-gold-cloud border-amber-500/20"
                          : "bg-primary/10 text-primary border-primary/20"
                      }`}
                    >
                      {component.scope.replace(/_/g, " ").toLowerCase()}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">{component.purpose}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
