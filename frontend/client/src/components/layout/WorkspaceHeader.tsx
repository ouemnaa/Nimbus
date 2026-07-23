interface WorkspaceHeaderProps {
  title: string;
  subtitle?: string;
}

export default function WorkspaceHeader({
  title,
  subtitle,
}: WorkspaceHeaderProps) {
  return (
    <div className="border-b border-border/50 bg-background/70 px-5 py-4 backdrop-blur-sm">
      <div className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-primary/80">
          Solution Architect Workspace
        </p>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        {subtitle ? (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
    </div>
  );
}
