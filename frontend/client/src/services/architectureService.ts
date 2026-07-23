import type {
  AnalyzeArchitectureRequest,
  AnalyzeArchitectureResponse,
} from "@/types/architecture";

export const ARCHITECT_AGENT_URL = (
  import.meta.env.VITE_ARCHITECT_AGENT_URL as string | undefined
)?.replace(/\/+$/, "");

export async function analyzeArchitecture(
  request: AnalyzeArchitectureRequest
): Promise<AnalyzeArchitectureResponse> {
  if (!ARCHITECT_AGENT_URL) {
    throw new Error("Missing VITE_ARCHITECT_AGENT_URL");
  }

  let response: Response;

  try {
    response = await fetch(
      `${ARCHITECT_AGENT_URL}/api/v1/architectures/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      }
    );
  } catch {
    throw new Error(
      `Could not reach the Solution Architect Agent. Make sure the agent is running on ${ARCHITECT_AGENT_URL}.`
    );
  }

  if (!response.ok) {
    let message = "Architecture analysis failed.";

    try {
      const errorBody = (await response.json()) as {
        detail?: string;
        message?: string;
      };
      message = errorBody.detail || errorBody.message || message;
    } catch {
      // Keep the clean fallback when the server does not return JSON.
    }

    throw new Error(message);
  }

  try {
    return (await response.json()) as AnalyzeArchitectureResponse;
  } catch {
    throw new Error("The Solution Architect Agent returned an invalid response.");
  }
}
