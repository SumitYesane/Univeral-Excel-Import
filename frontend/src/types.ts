export type ImportResponse = {
  job_id: string;
  status: string;
  created_at?: string | null;
};

export type JobStatus = {
  job_id: string;
  tenant_id: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  success_rows: number;
  failed_rows: number;
  error_file_url?: string | null;
  error_message?: string | null;
  original_filename?: string | null;
  profile_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

export type JobListResponse = {
  jobs: JobStatus[];
};

export type ImportProfile = {
  tenant_id: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  filename_contains: string[];
  required_headers: string[];
  sheet_mapping?: Record<string, string[]> | null;
};

export type ImportProfileListResponse = {
  profiles: ImportProfile[];
};
