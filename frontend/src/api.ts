import type { ImportProfileListResponse, ImportResponse, JobListResponse, JobStatus } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

type RequestOptions = {
  apiKey?: string;
  tenantId?: string;
};

async function apiRequest<T>(path: string, init: RequestInit = {}, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (options.apiKey) {
    headers.set("X-API-Key", options.apiKey);
  }
  if (options.tenantId) {
    headers.set("X-Tenant-ID", options.tenantId);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function createImportJob(formData: FormData, options: RequestOptions): Promise<ImportResponse> {
  return apiRequest<ImportResponse>("/imports/upload", { method: "POST", body: formData }, options);
}

export async function getJob(jobId: string, options: RequestOptions): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/import/status/${jobId}`, { method: "GET" }, options);
}

export async function listJobs(tenantId: string, options: RequestOptions): Promise<JobListResponse> {
  const query = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return apiRequest<JobListResponse>(`/jobs${query}`, { method: "GET" }, options);
}

export async function listProfiles(tenantId: string, options: RequestOptions): Promise<ImportProfileListResponse> {
  return apiRequest<ImportProfileListResponse>(`/profiles/${encodeURIComponent(tenantId)}`, { method: "GET" }, options);
}

export async function downloadErrorFile(jobId: string, options: RequestOptions): Promise<Blob> {
  const headers = new Headers();
  if (options.apiKey) {
    headers.set("X-API-Key", options.apiKey);
  }
  if (options.tenantId) {
    headers.set("X-Tenant-ID", options.tenantId);
  }

  const response = await fetch(`${API_BASE_URL}/import/errors/${jobId}`, {
    method: "GET",
    headers
  });

  if (!response.ok) {
    let detail = "Download failed";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.blob();
}
