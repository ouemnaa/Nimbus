interface WorkspaceHeaderProps {
  title: string;
  subtitle?: string;
}

export default function WorkspaceHeader({
  title,
  subtitle,
}: WorkspaceHeaderProps) {
  return (
    <div className="border-b border-gold-soft/15 bg-[#0D131D]/90 px-5 py-4 backdrop-blur-md">
      <div className="space-y-1">
        <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-gold-cloud">
          Solution Architect Workspace
        </p>
        <h1 className="text-lg font-semibold text-[#F7EEDC]">{title}</h1>
        {subtitle ? (
          <p className="text-sm text-[#AFA79A]">{subtitle}</p>
        ) : null}
      </div>
    </div>
  );
}
