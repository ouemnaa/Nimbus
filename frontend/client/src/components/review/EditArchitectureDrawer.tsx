import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { CanonicalArchitecture, RequirementContext } from "@/types/architecture";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface EditArchitectureDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  architecture: CanonicalArchitecture;
  onSave: (updates: Partial<CanonicalArchitecture>) => void;
}

export default function EditArchitectureDrawer({
  open,
  onOpenChange,
  architecture,
  onSave,
}: EditArchitectureDrawerProps) {
  const [environment, setEnvironment] = useState(
    architecture.requirement_summary.environment
  );
  const [region, setRegion] = useState(architecture.cloud.region);
  const [budgetPreference, setBudgetPreference] = useState(
    architecture.requirement_summary.budget_preference
  );
  const [availabilityRequirement, setAvailabilityRequirement] = useState(
    architecture.requirement_summary.availability_requirement
  );

  const handleSave = () => {
    onSave({
      requirement_summary: {
        ...architecture.requirement_summary,
        environment,
        budget_preference: budgetPreference,
        availability_requirement: availabilityRequirement,
      },
      cloud: {
        ...architecture.cloud,
        region,
      },
    });
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:w-96">
        <SheetHeader>
          <SheetTitle>Edit Architecture Properties</SheetTitle>
          <SheetDescription>
            Modify high-level architecture parameters.
          </SheetDescription>
        </SheetHeader>

        <Alert className="mt-4 border-amber-500/20 bg-amber-500/5">
          <AlertCircle className="h-4 w-4 text-amber-400" />
          <AlertDescription className="text-xs text-amber-400">
            Changes are local in this frontend prototype. In the complete platform they will create
            a new reviewed architecture version.
          </AlertDescription>
        </Alert>

        <div className="space-y-4 mt-6">
          <div>
            <label className="text-sm font-medium text-foreground">Environment</label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value as any)}
              className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Region</label>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="eu-west-1">eu-west-1 (Ireland)</option>
              <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
              <option value="us-east-1">us-east-1 (N. Virginia)</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Budget Preference</label>
            <select
              value={budgetPreference}
              onChange={(e) => setBudgetPreference(e.target.value as any)}
              className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="MINIMIZE_COST">Minimize Cost</option>
              <option value="BALANCED">Balanced</option>
              <option value="PERFORMANCE_FIRST">Performance First</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Availability Requirement</label>
            <select
              value={availabilityRequirement}
              onChange={(e) => setAvailabilityRequirement(e.target.value as any)}
              className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="STANDARD">Standard</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
            Cancel
          </Button>
          <Button onClick={handleSave} className="flex-1">
            Save Changes
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

