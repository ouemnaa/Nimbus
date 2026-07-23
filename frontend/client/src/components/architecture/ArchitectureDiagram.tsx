import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from "lucide-react";
import mermaid from "mermaid";

interface ArchitectureDiagramProps {
  diagram: string;
  title: string;
}

export default function ArchitectureDiagram({ diagram, title }: ArchitectureDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        mermaid.initialize({ startOnLoad: true, theme: "dark" });
        const { svg } = await mermaid.render("diagram-" + Math.random(), diagram);
        containerRef.current.innerHTML = svg;
        setError(null);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setError("Failed to render diagram");
      }
    };

    renderDiagram();
  }, [diagram]);

  const handleZoom = (direction: "in" | "out") => {
    setScale((prev) => {
      const newScale = direction === "in" ? prev + 0.1 : prev - 0.1;
      return Math.max(0.5, Math.min(newScale, 2));
    });
  };

  return (
    <Card className="p-4 bg-background border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8"
            onClick={() => handleZoom("out")}
            disabled={scale <= 0.5}
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          <span className="text-xs text-muted-foreground w-10 text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8"
            onClick={() => handleZoom("in")}
            disabled={scale >= 2}
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8"
            onClick={() => setScale(1)}
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" className="w-8 h-8">
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive">
          {error}
        </div>
      ) : (
        <div
          className="overflow-auto bg-card/50 rounded border border-border p-4 flex items-center justify-center min-h-96"
          style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
        >
          <div ref={containerRef} className="w-full" />
        </div>
      )}
    </Card>
  );
}

