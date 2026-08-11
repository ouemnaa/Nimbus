import { useState } from "react";
import { Link } from "wouter";
import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Plus } from "lucide-react";
import { mockProjects } from "@/data/mockArchitecture";
import { formatDate, formatStatus } from "@/utils/format";
import { motion } from "framer-motion";

export default function ProjectsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filteredProjects = mockProjects.filter((project) => {
    const matchesSearch = project.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = !statusFilter || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusColors: Record<string, string> = {
    APPROVED: "bg-emerald-500/10 text-emerald-400",
    READY_FOR_REVIEW: "bg-gold-soft/10 text-gold-cloud",
    NEEDS_CLARIFICATION: "bg-amber-500/10 text-amber-400",
  };

  return (
    <AppShell>
      <div className="flex-1 overflow-auto bg-transparent">
        <div className="max-w-5xl mx-auto px-6 py-8">
          {/* Header */}
          <motion.div
            className="flex items-center justify-between mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-text-primary via-primary to-text-secondary bg-clip-text text-transparent">
                Architecture Projects
              </h1>
              <p className="text-text-muted mt-1">Manage and review your architectures</p>
            </div>
            <Link href="/">
              <Button className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow transition-all duration-300 font-semibold">
                <Plus className="w-4 h-4" />
                New Architecture
              </Button>
            </Link>
          </motion.div>

          {/* Search and Filters */}
          <motion.div
            className="space-y-4 mb-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search projects..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-card border-border focus-visible:ring-primary focus-visible:border-primary transition-all duration-300 text-text-primary placeholder:text-text-muted"
              />
            </div>

            <div className="flex gap-2">
              {["All", "Ready for review", "Needs clarification", "Approved"].map((filter) => (
                <Button
                  key={filter}
                  variant={
                    (filter === "All" && !statusFilter) ||
                    (filter !== "All" &&
                      statusFilter ===
                        filter
                          .toUpperCase()
                          .replace(/\s+/g, "_"))
                      ? "default"
                      : "outline"
                  }
                  size="sm"
                  onClick={() => {
                    if (filter === "All") {
                      setStatusFilter(null);
                    } else {
                      setStatusFilter(
                        filter
                          .toUpperCase()
                          .replace(/\s+/g, "_")
                      );
                    }
                  }}
                >
                  {filter}
                </Button>
              ))}
            </div>
          </motion.div>

          {/* Projects List */}
          <motion.div
            className="space-y-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {filteredProjects.map((project) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <Link href={`/workspace/${project.id}`}>
                  <Card className="p-4 bg-card border-border hover:border-gold-soft/50 transition-all cursor-pointer shadow-sm hover:shadow-md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-text-primary group-hover:text-gold-soft transition-colors">
                        {project.title}
                      </h3>
                      <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                        {project.requirement}
                      </p>
                      <div className="flex items-center gap-3 mt-3 text-xs text-text-muted">
                        <span>AWS</span>
                        <span>•</span>
                        <span>{project.context?.environment || "development"}</span>
                        <span>•</span>
                        <span>{project.resourceCount || 6} resources</span>
                        <span>•</span>
                        <span>v{project.architecture?.architecture_version || 1}</span>
                        <span>•</span>
                        <span>{formatDate(project.updatedAt)}</span>
                      </div>
                    </div>
                    <Badge className={`${statusColors[project.status]} text-xs whitespace-nowrap`}>
                      {formatStatus(project.status)}
                    </Badge>
                  </div>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </motion.div>

          {filteredProjects.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}>
              <Card className="p-12 text-center bg-card border-border">
              <p className="text-text-muted">No projects found</p>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
