import { useEffect, useMemo, useState } from "react";
import { Link } from "wouter";
import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { listProjects } from "@/services/architectureService";
import type { ArchitectureStatus, BackendProject } from "@/types/architecture";
import { formatDate, formatStatus } from "@/utils/format";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  FileCode2,
  FolderOpen,
  Plus,
  Search,
  Sparkles,
} from "lucide-react";

type ProjectFilter =
  | "ALL"
  | "READY_FOR_REVIEW"
  | "TERRAFORM_GENERATED"
  | "APPROVED"
  | "NEEDS_REVIEW";

const PROJECT_FILTERS: Array<{ label: string; value: ProjectFilter }> = [
  { label: "All", value: "ALL" },
  { label: "Ready for review", value: "READY_FOR_REVIEW" },
  { label: "Terraform generated", value: "TERRAFORM_GENERATED" },
  { label: "Approved", value: "APPROVED" },
  { label: "Needs review", value: "NEEDS_REVIEW" },
];

const PAGE_SIZE = 8;

const statusColors: Record<string, string> = {
  APPROVED: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  READY_FOR_REVIEW:
    "bg-gold-soft/10 text-gold-cloud border border-gold-soft/25",
  NEEDS_CLARIFICATION:
    "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  UNSUPPORTED: "bg-red-500/10 text-red-300 border border-red-500/20",
  DRAFT_REVISION: "bg-blue-500/10 text-blue-300 border border-blue-500/20",
};

function terraformBadgeClass(status: string | null): string {
  if (status === "SUCCESS") {
    return "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20";
  }
  if (status === "NEEDS_REVIEW") {
    return "bg-amber-500/10 text-amber-300 border border-amber-500/20";
  }
  if (status) {
    return "bg-slate-500/10 text-slate-300 border border-slate-500/20";
  }
  return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
}

function projectEnvironment(project: BackendProject): string {
  const environment = project.context?.environment;
  return typeof environment === "string" && environment.trim()
    ? environment
    : "development";
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<BackendProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilter, setActiveFilter] = useState<ProjectFilter>("ALL");
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    listProjects()
      .then(items => {
        if (isMounted) {
          setProjects(items);
        }
      })
      .catch(loadError => {
        if (isMounted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Could not load persisted projects."
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredProjects = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return projects.filter(project => {
      const matchesSearch =
        !query ||
        project.title.toLowerCase().includes(query) ||
        project.initialRequirement.toLowerCase().includes(query) ||
        project.slug.toLowerCase().includes(query);
      const matchesFilter =
        activeFilter === "ALL" ||
        (activeFilter === "READY_FOR_REVIEW" &&
          project.status === "READY_FOR_REVIEW") ||
        (activeFilter === "TERRAFORM_GENERATED" &&
          project.hasTerraformGeneration) ||
        (activeFilter === "APPROVED" && project.status === "APPROVED") ||
        (activeFilter === "NEEDS_REVIEW" &&
          project.latestTerraformStatus === "NEEDS_REVIEW");
      return matchesSearch && matchesFilter;
    });
  }, [activeFilter, projects, searchTerm]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, activeFilter]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredProjects.length / PAGE_SIZE)
  );
  const paginatedProjects = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredProjects.slice(start, start + PAGE_SIZE);
  }, [currentPage, filteredProjects]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  return (
    <AppShell>
      <div className="flex-1 overflow-auto bg-transparent">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <motion.div
            className="mb-8 flex items-center justify-between gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div>
              <h1 className="bg-gradient-to-r from-text-primary via-primary to-text-secondary bg-clip-text text-4xl font-bold text-transparent">
                YourMulti-Game Serverless Backend Architecture Projects
              </h1>
              <p className="mt-1 text-text-muted">
                Reopen saved architectures and existing Terraform outputs
                without spending more tokens.
              </p>
            </div>
            <Link href="/">
              <Button className="gap-2 bg-primary text-primary-foreground shadow-sm transition-all duration-300 hover:bg-primary/90 hover:shadow">
                <Plus className="h-4 w-4" />
                New Architecture
              </Button>
            </Link>
          </motion.div>

          <motion.div
            className="mb-6 space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-muted-foreground" />
              <Input
                placeholder="Search by title, requirement, or slug..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="border-border bg-card pl-10 text-text-primary transition-all duration-300 placeholder:text-text-muted focus-visible:border-primary focus-visible:ring-primary"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {PROJECT_FILTERS.map(filter => (
                <Button
                  key={filter.label}
                  variant={
                    activeFilter === filter.value ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => setActiveFilter(filter.value)}
                >
                  {filter.label}
                </Button>
              ))}
            </div>
          </motion.div>

          {error ? (
            <Card className="mb-6 border border-red-400/25 bg-red-950/20 p-4 text-sm text-red-100 shadow-none">
              <div className="flex gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p>{error}</p>
                  <p className="mt-1 text-red-200/80">
                    Your projects should still be in the database; this page
                    just could not load them right now.
                  </p>
                </div>
              </div>
            </Card>
          ) : null}

          {isLoading ? (
            <motion.div
              className="space-y-3"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
            >
              {Array.from({ length: 3 }).map((_, index) => (
                <Card
                  key={index}
                  className="border-border bg-card p-5 shadow-none"
                >
                  <div className="space-y-3">
                    <div className="h-5 w-56 animate-pulse rounded bg-slate-700/40" />
                    <div className="h-4 w-full animate-pulse rounded bg-slate-700/30" />
                    <div className="h-4 w-2/3 animate-pulse rounded bg-slate-700/30" />
                  </div>
                </Card>
              ))}
            </motion.div>
          ) : filteredProjects.length > 0 ? (
            <motion.div
              className="space-y-3"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <div className="flex items-center justify-between gap-3 rounded-2xl border border-border/50 bg-bg-surface-soft/60 px-4 py-3 text-sm text-text-muted">
                <span>
                  Showing {paginatedProjects.length} of{" "}
                  {filteredProjects.length} matching projects
                </span>
                <span>
                  Page {currentPage} of {totalPages}
                </span>
              </div>

              {paginatedProjects.map(project => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                >
                  <Link href={`/workspace/${project.id}`}>
                    <Card className="group cursor-pointer border-border bg-card p-5 shadow-sm transition-all hover:border-gold-soft/50 hover:shadow-md">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-base font-semibold text-text-primary transition-colors group-hover:text-gold-soft">
                              {project.title}
                            </h3>
                            <Badge
                              className={`${statusColors[project.status] || "bg-slate-500/10 text-slate-300 border border-slate-500/20"} text-xs whitespace-nowrap`}
                            >
                              {formatStatus(project.status)}
                            </Badge>
                            <Badge
                              className={`${terraformBadgeClass(project.latestTerraformStatus)} text-xs whitespace-nowrap`}
                            >
                              {project.hasTerraformGeneration
                                ? `Terraform ${project.latestTerraformStatus || "saved"}`
                                : "No Terraform yet"}
                            </Badge>
                          </div>

                          <p className="mt-2 line-clamp-2 text-sm text-text-secondary">
                            {project.initialRequirement}
                          </p>

                          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-text-muted">
                            <span className="inline-flex items-center gap-1.5">
                              <Sparkles className="h-3.5 w-3.5" />
                              {projectEnvironment(project)}
                            </span>
                            <span>v{project.currentVersion || "1.0.0"}</span>
                            <span>{project.resourceCount} resources</span>
                            <span>
                              {formatDate(new Date(project.updatedAt))}
                            </span>
                            {project.latestTerraformUpdatedAt ? (
                              <span className="inline-flex items-center gap-1.5">
                                <FileCode2 className="h-3.5 w-3.5" />
                                Terraform saved{" "}
                                {formatDate(
                                  new Date(project.latestTerraformUpdatedAt)
                                )}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="hidden shrink-0 rounded-2xl border border-border/60 bg-bg-surface-soft/70 p-3 text-right md:block">
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            Workspace
                          </p>
                          <p className="mt-1 inline-flex items-center gap-2 text-sm text-text-primary">
                            <FolderOpen className="h-4 w-4" />
                            Open project
                          </p>
                        </div>
                      </div>
                    </Card>
                  </Link>
                </motion.div>
              ))}

              {totalPages > 1 ? (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/50 bg-bg-surface-soft/60 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setCurrentPage(page => Math.max(1, page - 1))
                      }
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setCurrentPage(page => Math.min(totalPages, page + 1))
                      }
                      disabled={currentPage === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ) : null}
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6 }}
            >
              <Card className="border-border bg-card p-12 text-center">
                <p className="text-text-muted">
                  {projects.length === 0
                    ? "No persisted projects yet. Generate an architecture and it will appear here."
                    : "No projects match your current filters."}
                </p>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
