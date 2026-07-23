import { Link, useLocation } from "wouter";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import {
  Zap,
  Layers,
  FolderOpen,
  Zap as Activity,
  Settings,
  Moon,
  Sun,
  User,
} from "lucide-react";
import { brand } from "@/config/brand";
import { useTheme } from "@/contexts/ThemeContext";

export default function NavigationRail() {
  const [location] = useLocation();
  const { theme, toggleTheme, switchable } = useTheme();

  const isActive = (path: string) => location === path;

  const navItems = [
    { icon: Layers, label: "Workspace", path: "/workspace/demo-architecture" },
    { icon: FolderOpen, label: "Projects", path: "/projects" },
    { icon: Activity, label: "Activity", path: "#", disabled: true },
  ];

  return (
    <div className="w-[68px] bg-card border-r border-border flex flex-col items-center py-4 gap-4 h-screen">
      {/* Logo */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg w-10 h-10 bg-primary/10 hover:bg-primary/20 text-primary"
            >
              <span className="font-bold text-lg">{brand.shortName}</span>
            </Button>
          </Link>
        </TooltipTrigger>
        <TooltipContent side="right">{brand.name}</TooltipContent>
      </Tooltip>

      {/* New Architecture Button */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg w-10 h-10 hover:bg-accent/20 text-accent"
            >
              <Zap className="w-5 h-5" />
            </Button>
          </Link>
        </TooltipTrigger>
        <TooltipContent side="right">New Architecture</TooltipContent>
      </Tooltip>

      {/* Navigation Items */}
      <div className="flex flex-col gap-2">
        {navItems.map((item) => (
          <Tooltip key={item.path}>
            <TooltipTrigger asChild>
              {item.disabled ? (
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-lg w-10 h-10 opacity-50 cursor-not-allowed"
                  disabled
                >
                  <item.icon className="w-5 h-5" />
                </Button>
              ) : (
                <Link href={item.path}>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={`rounded-lg w-10 h-10 ${
                      isActive(item.path)
                        ? "bg-primary/20 text-primary"
                        : "hover:bg-accent/10 text-muted-foreground"
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                  </Button>
                </Link>
              )}
            </TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom Controls */}
      <div className="flex flex-col gap-2">
        {/* Theme Toggle */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg w-10 h-10 hover:bg-accent/10 text-muted-foreground"
              onClick={toggleTheme}
              disabled={!switchable}
            >
              {theme === "dark" ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </TooltipContent>
        </Tooltip>

        {/* Settings */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Link href="/settings">
              <Button
                variant="ghost"
                size="icon"
                className={`rounded-lg w-10 h-10 ${
                  isActive("/settings")
                    ? "bg-primary/20 text-primary"
                    : "hover:bg-accent/10 text-muted-foreground"
                }`}
              >
                <Settings className="w-5 h-5" />
              </Button>
            </Link>
          </TooltipTrigger>
          <TooltipContent side="right">Settings</TooltipContent>
        </Tooltip>

        {/* Profile Avatar */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg w-10 h-10 bg-primary/10 hover:bg-primary/20 text-primary"
            >
              <User className="w-5 h-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">Profile</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
