import { Link, useLocation } from "wouter";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import {
  Plus,
  Layers,
  FolderOpen,
  Activity,
  Settings,
  Moon,
  Sun,
  User,
} from "lucide-react";
import { brand } from "@/config/brand";
import { useTheme } from "@/contexts/ThemeContext";
import logo from "@shared/logo.png";

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
    <div className="w-[70px] bg-[#0A0E17]/95 border-r border-gold-soft/15 flex flex-col items-center py-4 gap-4 h-screen backdrop-blur-2xl z-20">
      {/* Logo */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/">
            <Button
              variant="ghost"
              size="icon"
              className="h-12 w-12 rounded-2xl border border-gold-soft/30 bg-gradient-to-br from-gold-soft/10 to-bronze-muted/10 p-1 transition-all duration-300 hover:border-gold-soft/60 shadow-[0_0_20px_rgba(249,217,171,0.15)]"
            >
              <img
                src={logo}
                alt={`${brand.name} logo`}
                className="h-full w-full rounded-xl object-cover"
              />
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
              className="rounded-xl w-10 h-10 bg-gold-soft/10 hover:bg-gold-soft/20 text-gold-cloud border border-gold-soft/25 transition-all duration-200"
            >
              <Plus className="w-5 h-5" />
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
                  className="rounded-xl w-10 h-10 opacity-40 cursor-not-allowed text-text-muted"
                  disabled
                >
                  <item.icon className="w-5 h-5" />
                </Button>
              ) : (
                <Link href={item.path}>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={`rounded-xl w-10 h-10 transition-all ${
                      isActive(item.path)
                        ? "bg-gold-soft/15 text-gold-soft border border-gold-soft/35 shadow-[0_0_15px_rgba(249,217,171,0.15)]"
                        : "hover:bg-gold-soft/10 text-text-secondary hover:text-gold-soft"
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
              className="rounded-xl w-10 h-10 hover:bg-gold-soft/10 text-text-secondary hover:text-gold-soft transition-colors"
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
                className={`rounded-xl w-10 h-10 transition-all ${
                  isActive("/settings")
                    ? "bg-gold-soft/15 text-gold-soft border border-gold-soft/35 shadow-[0_0_15px_rgba(249,217,171,0.15)]"
                    : "hover:bg-gold-soft/10 text-text-secondary hover:text-gold-soft"
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
              className="rounded-xl w-10 h-10 bg-gold-soft/10 hover:bg-gold-soft/20 text-text-primary hover:text-gold-soft transition-colors border border-gold-soft/20"
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
