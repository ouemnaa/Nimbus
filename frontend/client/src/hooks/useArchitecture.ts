import { useState, useCallback } from "react";
import { CanonicalArchitecture, ArchitectureStatus } from "@/types/architecture";

export function useArchitecture(initialArchitecture: CanonicalArchitecture) {
  const [architecture, setArchitecture] = useState<CanonicalArchitecture>(initialArchitecture);
  const [status, setStatus] = useState<ArchitectureStatus>(initialArchitecture.status);

  const updateStatus = useCallback((newStatus: ArchitectureStatus) => {
    setStatus(newStatus);
    setArchitecture((prev) => ({
      ...prev,
      status: newStatus,
    }));
  }, []);

  const updateArchitecture = useCallback((updates: Partial<CanonicalArchitecture>) => {
    setArchitecture((prev) => ({
      ...prev,
      ...updates,
    }));
  }, []);

  return {
    architecture,
    status,
    updateStatus,
    updateArchitecture,
  };
}

