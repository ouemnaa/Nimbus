interface WorkspaceHeaderProps {
  title: string;
  subtitle?: string;
}

export default function WorkspaceHeader({
  title,
  subtitle,
}: WorkspaceHeaderProps) {
  return (
    <div className="border-b border-border/40 bg-bg-surface/90 px-5 py-4 backdrop-blur-md">
      <div className="space-y-1">
        <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">
          Solution Architect Workspace
        </p>
        <h1 className="text-lg font-semibold text-text-primary">{title}</h1>
        {subtitle ? (
          <p className="text-sm text-text-muted">{subtitle}</p>
        ) : null}
      </div>
    </div>
  );
}
