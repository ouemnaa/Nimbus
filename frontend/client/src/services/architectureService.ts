import type {
  AnalyzeArchitectureRequest,
  AnalyzeArchitectureResponse,
  ProjectMessageResponse,
  ProjectWorkspaceResponse,
  TerraformGeneration,
} from "@/types/architecture";

export const NIMBUS_BACKEND_URL = (
  (import.meta.env.VITE_NIMBUS_BACKEND_URL as string | undefined) ||
  "http://localhost:8000"
).replace(/\/+$/, "");

async function requestJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${NIMBUS_BACKEND_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      `Could not reach the Nimbus backend. Make sure it is running on ${NIMBUS_BACKEND_URL}.`
    );
  }

  if (!response.ok) {
    let message = "Nimbus backend request failed.";

    try {
      const errorBody = (await response.json()) as {
        detail?: string | { message?: string };
        message?: string;
      };
      message =
        (typeof errorBody.detail === "object" && errorBody.detail?.message) ||
        (typeof errorBody.detail === "string" && errorBody.detail) ||
        errorBody.message ||
        message;
    } catch {
      // Keep the clean fallback when the backend does not return JSON.
    }

    throw new Error(message);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("Nimbus backend returned an invalid response.");
  }
}

export async function createProject(
  request: AnalyzeArchitectureRequest
): Promise<ProjectWorkspaceResponse> {
  return requestJson<ProjectWorkspaceResponse>("/api/projects", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getProjectWorkspace(
  projectId: string
): Promise<ProjectWorkspaceResponse> {
  return requestJson<ProjectWorkspaceResponse>(
    `/api/projects/${encodeURIComponent(projectId)}`
  );
}

export async function sendProjectMessage(
  projectId: string,
  message: string
): Promise<ProjectMessageResponse> {
  return requestJson<ProjectMessageResponse>(
    `/api/projects/${encodeURIComponent(projectId)}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ message }),
    }
  );
}

export async function acceptDraftVersion(
  projectId: string,
  versionId: string
): Promise<ProjectWorkspaceResponse> {
  return requestJson<ProjectWorkspaceResponse>(
    `/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(
      versionId
    )}/accept`,
    { method: "POST" }
  );
}

export async function discardDraftVersion(
  projectId: string,
  versionId: string
): Promise<ProjectWorkspaceResponse> {
  return requestJson<ProjectWorkspaceResponse>(
    `/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(
      versionId
    )}/discard`,
    { method: "POST" }
  );
}

export async function generateTerraform(
  projectId: string
): Promise<TerraformGeneration> {
  return requestJson<TerraformGeneration>(
    `/api/projects/${encodeURIComponent(projectId)}/terraform/generate`,
    { method: "POST" }
  );
}

export async function getLatestTerraformGeneration(
  projectId: string
): Promise<TerraformGeneration | null> {
  let response: Response;

  try {
    response = await fetch(
      `${NIMBUS_BACKEND_URL}/api/projects/${encodeURIComponent(
        projectId
      )}/terraform/latest`
    );
  } catch {
    throw new Error(
      `Could not reach the Nimbus backend. Make sure it is running on ${NIMBUS_BACKEND_URL}.`
    );
  }

  if (response.status === 204) {
    return null;
  }
  if (!response.ok) {
    throw new Error("Could not load generated Terraform files.");
  }
  return (await response.json()) as TerraformGeneration;
}

export async function analyzeArchitecture(
  request: AnalyzeArchitectureRequest
): Promise<AnalyzeArchitectureResponse & { projectId: string }> {
  const workspace = await createProject(request);
  if (!workspace.currentVersion) {
    throw new Error("Nimbus backend did not return a current architecture version.");
  }

  return {
    projectId: workspace.project.id,
    architecture: workspace.currentVersion.architecture,
    report_markdown: workspace.currentVersion.reportMarkdown,
    metadata: workspace.currentVersion.metadata as AnalyzeArchitectureResponse["metadata"],
  };
}
