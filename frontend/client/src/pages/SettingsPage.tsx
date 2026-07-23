import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const { theme } = useTheme();
  const [density, setDensity] = useLocalStorage("ui-density", "comfortable");
  const [autoFitDiagrams, setAutoFitDiagrams] = useLocalStorage("auto-fit-diagrams", true);
  const [showNetworkDiagram, setShowNetworkDiagram] = useLocalStorage(
    "show-network-diagram",
    true
  );
  const [animationDuration, setAnimationDuration] = useLocalStorage(
    "animation-duration",
    "normal"
  );

  const handleResetData = () => {
    if (confirm("Are you sure? This will reset all frontend demo data.")) {
      localStorage.clear();
      toast.success("Frontend demo data reset");
    }
  };

  return (
    <AppShell>
      <div className="flex-1 overflow-auto bg-gradient-to-b from-background via-background to-primary/5">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <motion.h1
            className="text-4xl font-bold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            Settings
          </motion.h1>

          {/* Appearance */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <Card className="p-6 bg-gradient-to-br from-card to-card/50 border border-border/50 hover:border-primary/30 transition-all duration-300 mb-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Appearance</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">Theme</label>
                <p className="text-xs text-muted-foreground mt-1">
                  Current theme: <span className="capitalize">{theme}</span>
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Use the theme toggle in the navigation rail to switch themes.
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-foreground">Density</label>
                <div className="flex gap-2 mt-2">
                  {["comfortable", "compact"].map((option) => (
                    <Button
                      key={option}
                      variant={density === option ? "default" : "outline"}
                      size="sm"
                      onClick={() => setDensity(option)}
                      className="capitalize hover:bg-primary/10 transition-all duration-200"
                    >
                      {option}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
            </Card>
          </motion.div>

          {/* Diagram Preferences */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Card className="p-6 bg-gradient-to-br from-card to-card/50 border border-border/50 hover:border-primary/30 transition-all duration-300 mb-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Diagram Preferences</h2>
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoFitDiagrams}
                  onChange={(e) => setAutoFitDiagrams(e.target.checked)}
                  className="w-4 h-4 rounded border-border"
                />
                <span className="text-sm text-foreground">Automatically fit diagrams to view</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showNetworkDiagram}
                  onChange={(e) => setShowNetworkDiagram(e.target.checked)}
                  className="w-4 h-4 rounded border-border"
                />
                <span className="text-sm text-foreground">Show network diagram when available</span>
              </label>
            </div>
            </Card>
          </motion.div>

          {/* Demo Preferences */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Card className="p-6 bg-gradient-to-br from-card to-card/50 border border-border/50 hover:border-primary/30 transition-all duration-300 mb-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Demo Preferences</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">Analysis Animation Duration</label>
                <select
                  value={animationDuration}
                  onChange={(e) => setAnimationDuration(e.target.value)}
                  className="w-full mt-2 px-3 py-2 bg-gradient-to-br from-card/80 to-card/50 border border-border/50 focus:border-primary/50 rounded-md text-sm transition-all duration-300"
                >
                  <option value="fast">Fast</option>
                  <option value="normal">Normal</option>
                  <option value="slow">Slow</option>
                </select>
              </div>
            </div>
            </Card>
          </motion.div>

          {/* AI Provider Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-500/30 hover:border-amber-500/50 transition-all duration-300 mb-6">
            <h2 className="text-lg font-semibold text-foreground mb-2">AI Provider</h2>
            <p className="text-sm text-muted-foreground">
              Model selection is managed securely by the Agents Service and is not configured in the browser.
            </p>
            </Card>
          </motion.div>

          {/* Danger Zone */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border border-red-500/30 hover:border-red-500/50 transition-all duration-300">
            <h2 className="text-lg font-semibold text-red-400 mb-4">Danger Zone</h2>
            <Button
              variant="destructive"
              className="gap-2 hover:bg-red-600 transition-all duration-200"
              onClick={handleResetData}
            >
              <Trash2 className="w-4 h-4" />
              Reset Frontend Demo Data
            </Button>
            </Card>
          </motion.div>
        </div>
      </div>
    </AppShell>
  );
}
