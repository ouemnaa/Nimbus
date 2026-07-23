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
    <div className="space-y-6">
      {Object.entries(groupedByCategory).map(([category, items]) => (
        <div key={category}>
          <div className="flex items-center gap-2 mb-3">
            {categoryIcons[category]}
            <h3 className="text-sm font-semibold text-foreground">{category}</h3>
          </div>
          <div className="space-y-3">
            {items.map((component) => (
              <Card key={component.id} className="p-4 bg-background border-border">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h4 className="font-medium text-sm text-foreground">{component.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{component.type}</p>
                    <p className="text-sm text-muted-foreground mt-2">{component.purpose}</p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        component.scope === "public"
                          ? "bg-blue-500/10 text-blue-400"
                          : "bg-gray-500/10 text-gray-400"
                      }`}
                    >
                      {component.scope}
                    </span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

