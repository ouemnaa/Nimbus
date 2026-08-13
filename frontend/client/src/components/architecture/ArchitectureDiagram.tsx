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
    <Card className="p-6 dark:bg-black/40 bg-white/40 backdrop-blur-md dark:border-white/10 border-black/10 rounded-2xl shadow-xl relative group flex flex-col h-full border">
      <div className="flex items-center justify-between mb-6 shrink-0 relative z-10">
        <h3 className="text-sm font-bold dark:text-slate-100 text-slate-900 tracking-wide uppercase flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
          {title}
        </h3>
        <div className="flex items-center gap-1.5 dark:bg-black/40 bg-white/60 p-1.5 rounded-xl border dark:border-white/10 border-black/10 shadow-inner">
          <Button
            variant="ghost"
            size="icon"
            className="w-7 h-7 rounded-lg dark:hover:bg-white/10 hover:bg-black/5 dark:text-slate-300 text-slate-700"
            onClick={() => setScale(prev => Math.max(0.2, prev - 0.1))}
            disabled={scale <= 0.2}
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          <span className="text-[10px] font-mono dark:text-slate-400 text-slate-600 w-12 text-center font-bold tracking-widest">
            {Math.round(scale * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="w-7 h-7 rounded-lg dark:hover:bg-white/10 hover:bg-black/5 dark:text-slate-300 text-slate-700"
            onClick={() => setScale(prev => Math.min(3, prev + 0.1))}
            disabled={scale >= 3}
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          <div className="w-px h-4 dark:bg-white/10 bg-black/10 mx-1" />
          <Button
            variant="ghost"
            size="icon"
            className="w-7 h-7 rounded-lg dark:hover:bg-white/10 hover:bg-black/5 dark:text-slate-300 text-slate-700"
            onClick={handleReset}
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" className="w-7 h-7 rounded-lg dark:hover:bg-white/10 hover:bg-black/5 dark:text-slate-300 text-slate-700">
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-500 flex items-center justify-center min-h-[400px]">
          {error}
        </div>
      ) : (
        <div className="relative flex-1 min-h-[400px] rounded-xl border dark:border-white/5 border-black/5 overflow-hidden dark:bg-black/20 bg-white/60 shadow-inner group-hover:border-primary/20 transition-colors">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(var(--primary),0.05)_0%,transparent_70%)] pointer-events-none" />
          <div
            className="absolute inset-0 cursor-grab active:cursor-grabbing select-none"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            <div
              ref={containerRef}
              className="w-full h-full flex items-center justify-center p-8 transition-transform duration-75 ease-out origin-center"
              style={{
                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${scale})`,
              }}
            />
          </div>
        </div>
      )}
    </Card>
  );
}
