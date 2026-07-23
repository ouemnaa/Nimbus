import {
  AnalyzeArchitectureRequest,
  AnalyzeArchitectureResponse,
} from "@/types/architecture";
import { mockArchitecture } from "@/data/mockArchitecture";

export const architectureService = {
  async analyzeRequirement(
    request: AnalyzeArchitectureRequest
  ): Promise<AnalyzeArchitectureResponse> {
    await new Promise((resolve) => setTimeout(resolve, 600));

    return {
      projectId: "demo-architecture",
      architecture: {
        ...mockArchitecture,
        title: request.requirement.slice(0, 60) || mockArchitecture.title,
      },
    };
  },
};
