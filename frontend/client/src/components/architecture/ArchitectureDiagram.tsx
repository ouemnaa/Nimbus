import { useState, useRef, useEffect, useId } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from "lucide-react";
import mermaid from "mermaid";
import { useTheme } from "@/contexts/ThemeContext";

interface ArchitectureDiagramProps {
  diagram: string;
  title: string;
}

export default function ArchitectureDiagram({ diagram, title }: ArchitectureDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reactId = useId();
  const diagramId = `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [scale, setScale] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [error, setError] = useState<string | null>(null);
  const { theme } = useTheme();

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
          theme: theme === "dark" ? "dark" : "default",
          securityLevel: "loose",
          themeVariables: theme === "dark" ? {} : {
            background: "#FCFAF2",
            primaryColor: "#EFEBE0",
            primaryTextColor: "#231C16",
            lineColor: "#8E5E38",
            signalColor: "#8E5E38",
            signalTextColor: "#231C16",
          }
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
  }, [diagram, diagramId, theme]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomIntensity = 0.05;
    const newScale = e.deltaY < 0 ? scale + zoomIntensity : scale - zoomIntensity;
    setScale(Math.max(0.2, Math.min(newScale, 3)));
  };

  const handleReset = () => {
    setScale(1);
    setPanOffset({ x: 0, y: 0 });
  };

  return (
    <Card className="p-4 bg-card border-border/40">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8"
            onClick={() => setScale(prev => Math.max(0.2, prev - 0.1))}
            disabled={scale <= 0.2}
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
            onClick={() => setScale(prev => Math.min(3, prev + 0.1))}
            disabled={scale >= 3}
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="w-8 h-8"
            onClick={handleReset}
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
          className="relative overflow-hidden bg-bg-surface rounded border border-gold-soft/12 min-h-96 cursor-grab active:cursor-grabbing select-none flex items-center justify-center"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <div
            ref={containerRef}
            className="w-full flex items-center justify-center p-4 transition-transform duration-75 ease-out"
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${scale})`,
              transformOrigin: "center center",
            }}
          />
        </div>
      )}
    </Card>
  );
}
