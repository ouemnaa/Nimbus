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
      architecture: {
        ...mockArchitecture,
        title: request.requirement.slice(0, 60) || mockArchitecture.title,
      },
      report_markdown: mockArchitecture.markdown_report || "",
      metadata: {
        provider: "demo",
        model: "nimbus-demo-architecture",
        generation_duration_ms: 600,
      },
    };
  },
};
