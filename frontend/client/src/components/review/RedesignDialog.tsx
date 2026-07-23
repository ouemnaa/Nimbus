import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

interface RedesignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (feedback: string, targetArea: string) => void;
}

export default function RedesignDialog({
  open,
  onOpenChange,
  onSubmit,
}: RedesignDialogProps) {
  const [feedback, setFeedback] = useState("");
  const [targetArea, setTargetArea] = useState("Entire architecture");

  const handleSubmit = () => {
    if (feedback.trim()) {
      onSubmit(feedback, targetArea);
      setFeedback("");
      setTargetArea("Entire architecture");
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request Redesign</DialogTitle>
          <DialogDescription>
            Describe what should change in the architecture.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground">What should change?</label>
            <Textarea
              placeholder="e.g., Reduce the monthly cost, Replace ECS with EC2, Make the database highly available..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="mt-2 min-h-24"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Target area</label>
            <select
              value={targetArea}
              onChange={(e) => setTargetArea(e.target.value)}
              className="w-full mt-2 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="Entire architecture">Entire architecture</option>
              <option value="Compute">Compute</option>
              <option value="Networking">Networking</option>
              <option value="Database">Database</option>
              <option value="Security">Security</option>
              <option value="Cost">Cost</option>
              <option value="Scalability">Scalability</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!feedback.trim()}>
            Submit Redesign Request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

