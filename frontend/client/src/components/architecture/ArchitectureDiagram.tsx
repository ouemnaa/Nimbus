import { useState, useRef, useEffect, useId } from "react";
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
  const reactId = useId();
  const diagramId = `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [scale, setScale] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        const source = diagram
          .trim()
          .replace(/^```mermaid\s*/i, "")
          .replace(/```\s*$/, "")
          .trim();

        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose",
        });
        await mermaid.parse(source);
        const { svg, bindFunctions } = await mermaid.render(diagramId, source);

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          bindFunctions?.(containerRef.current);
          setError(null);
        }
      } catch (err) {
        console.error("Mermaid render error:", err);
        if (!cancelled) {
          setError("Failed to render diagram");
        }
      }
    };

    renderDiagram();
    return () => {
      cancelled = true;
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [diagram, diagramId]);

  const handleZoom = (direction: "in" | "out") => {
    setScale((prev) => {
      const newScale = direction === "in" ? prev + 0.1 : prev - 0.1;
      return Math.max(0.5, Math.min(newScale, 2));
    });
  };

  return (
    <Card className="p-4 bg-[rgba(17,22,29,0.82)] border-gold-soft/15">
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
          className="overflow-auto bg-bg-surface rounded border border-gold-soft/12 p-4 flex items-center justify-center min-h-96"
          style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
        >
          <div ref={containerRef} className="w-full" />
        </div>
      )}
    </Card>
  );
}
