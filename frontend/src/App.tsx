import { FormEvent, useEffect, useState } from "react";

import { createImportJob, downloadErrorFile, getJob, listJobs, listProfiles } from "./api";
import type { ImportProfile, JobStatus } from "./types";

function formatDate(value?: string | null) {
  if (!value) {
    return "Pending";
  }
  return new Date(value).toLocaleString();
}

type DatabaseType = "sqlite" | "postgresql" | "mysql" | "mssql";

function labelForDatabaseType(value: DatabaseType) {
  if (value === "mssql") {
    return "SQL Server";
  }
  if (value === "postgresql") {
    return "PostgreSQL";
  }
  if (value === "mysql") {
    return "MySQL";
  }
  return "SQLite";
}

function App() {
  const [apiKey, setApiKey] = useState("");
  const [tenantId, setTenantId] = useState("tenant_a");
  const [dbType, setDbType] = useState<DatabaseType>("sqlite");
  const [databaseName, setDatabaseName] = useState("demo_target.db");
  const [sqlitePath, setSqlitePath] = useState("demo_target.db");
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null);
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [profiles, setProfiles] = useState<ImportProfile[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "submitting">("idle");
  const [downloadState, setDownloadState] = useState<"idle" | "downloading">("idle");

  const completedJobs = jobs.filter((job) => job.status === "completed").length;
  const runningJobs = jobs.filter((job) => job.status === "running" || job.status === "queued").length;
  const failedRowsTotal = jobs.reduce((sum, job) => sum + job.failed_rows, 0);

  async function refreshJobs(selectedJobId?: string) {
    if (!tenantId) {
      return;
    }

    const response = await listJobs(tenantId, { apiKey, tenantId });
    setJobs(response.jobs);

    const jobId = selectedJobId || activeJob?.job_id;
    if (jobId) {
      const latest = response.jobs.find((job) => job.job_id === jobId);
      if (latest) {
        setActiveJob(latest);
        return;
      }
      const job = await getJob(jobId, { apiKey, tenantId });
      setActiveJob(job);
    }
  }

  useEffect(() => {
    void refreshJobs();
  }, [tenantId, apiKey]);

  useEffect(() => {
    async function refreshProfiles() {
      if (!tenantId) {
        setProfiles([]);
        return;
      }
      try {
        const response = await listProfiles(tenantId, { apiKey, tenantId });
        setProfiles(response.profiles);
      } catch (error) {
        setProfiles([]);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load import profiles");
      }
    }

    void refreshProfiles();
  }, [tenantId, apiKey]);

  useEffect(() => {
    if (!activeJob || !["queued", "running"].includes(activeJob.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshJobs(activeJob.job_id);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [activeJob?.job_id, activeJob?.status, tenantId, apiKey]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setErrorMessage("Choose a file before starting an import.");
      return;
    }

    setErrorMessage("");
    setSubmitState("submitting");

    try {
      const formData = new FormData();
      formData.append("tenant_id", tenantId);
      formData.append("db_type", dbType);
      if (dbType === "sqlite") {
        formData.append("sqlite_path", sqlitePath);
        formData.append("database_name", sqlitePath);
      } else {
        formData.append("database_name", databaseName);
        formData.append("host", host);
        if (port.trim()) {
          formData.append("port", port);
        }
        formData.append("username", username);
        formData.append("password", password);
      }
      formData.append("file", file);

      const created = await createImportJob(formData, { apiKey, tenantId });
      const job = await getJob(created.job_id, { apiKey, tenantId });
      setActiveJob(job);
      await refreshJobs(created.job_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Import request failed");
    } finally {
      setSubmitState("idle");
    }
  }

  async function handleDownloadErrorFile() {
    if (!activeJob) {
      return;
    }

    setErrorMessage("");
    setDownloadState("downloading");
    try {
      const blob = await downloadErrorFile(activeJob.job_id, { apiKey, tenantId });
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `${activeJob.job_id}_errors.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Error file download failed");
    } finally {
      setDownloadState("idle");
    }
  }

  return (
    <div className="app-shell">
      <div className="grid-noise" />
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="aurora aurora-c" />

      <section className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">UI</div>
          <div>
            <p className="eyebrow">Premium Import Operations</p>
            <h1 className="brand-title">Universal Import Console</h1>
          </div>
        </div>
        <div className="topbar-pills">
          <span className="topbar-pill">Tenant {tenantId}</span>
          <span className="topbar-pill">{profiles.length} Active Profiles</span>
          <span className="topbar-pill">{labelForDatabaseType(dbType)} Target</span>
        </div>
      </section>

      <header className="hero">
        <div className="hero-copy-block">
          <p className="eyebrow">Production Import Operations</p>
          <h2>Turn spreadsheet drops into a polished SaaS intake workflow.</h2>
          <p className="hero-copy">
            Upload a source file, let the backend resolve the right tenant profile automatically, and manage correction
            loops through downloadable error workbooks without exposing backend complexity to operators.
          </p>
        </div>
        <div className="hero-stats">
          <div className="hero-stat-card hero-stat-feature">
            <span>Automation Coverage</span>
            <strong>Profile-driven</strong>
            <p>Mapping, validation, and correction flow are all backend-managed.</p>
          </div>
          <div className="hero-stat-grid">
            <div className="hero-stat-card">
              <span>Completed</span>
              <strong>{completedJobs}</strong>
            </div>
            <div className="hero-stat-card">
              <span>In Flight</span>
              <strong>{runningJobs}</strong>
            </div>
            <div className="hero-stat-card">
              <span>Failed Rows</span>
              <strong>{failedRowsTotal}</strong>
            </div>
            <div className="hero-stat-card">
              <span>Database</span>
              <strong>{labelForDatabaseType(dbType)}</strong>
            </div>
          </div>
        </div>
      </header>

      <main className="layout">
        <section className="panel form-panel">
          <div className="panel-heading">
            <div>
              <h2>Start Import</h2>
              <p className="panel-subtitle">Minimal operator input, backend-managed orchestration.</p>
            </div>
            <span>{submitState === "submitting" ? "Submitting..." : `${profiles.length} profile(s)`}</span>
          </div>

          <form className="import-form" onSubmit={handleSubmit}>
            <div className="form-grid">
              <label>
                <span>API Key</span>
                <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Optional unless auth is enabled" />
              </label>

              <label>
                <span>Tenant ID</span>
                <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} required />
              </label>

              <label className="full-span">
                <span>Database Type</span>
                <select value={dbType} onChange={(event) => setDbType(event.target.value as DatabaseType)}>
                  <option value="sqlite">SQLite</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="mssql">SQL Server</option>
                </select>
              </label>
            </div>

            {dbType === "sqlite" ? (
              <div className="db-surface">
                <div className="db-surface-header">
                  <strong>SQLite Target</strong>
                  <p>Point the importer at a file-backed database used for the selected tenant.</p>
                </div>
                <label>
                  <span>SQLite File Path</span>
                  <input value={sqlitePath} onChange={(event) => setSqlitePath(event.target.value)} placeholder="demo_target.db" required />
                </label>
              </div>
            ) : (
              <div className="db-surface">
                <div className="db-surface-header">
                  <strong>{labelForDatabaseType(dbType)} Credentials</strong>
                  <p>Connection details are converted into a supported sync SQLAlchemy URL inside the backend.</p>
                </div>
                <div className="form-grid">
                  <label>
                    <span>Host</span>
                    <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="localhost" required />
                  </label>

                  <label>
                    <span>Port</span>
                    <input value={port} onChange={(event) => setPort(event.target.value)} placeholder={dbType === "postgresql" ? "5432" : dbType === "mysql" ? "3306" : "1433"} />
                  </label>

                  <label className="full-span">
                    <span>Database Name</span>
                    <input value={databaseName} onChange={(event) => setDatabaseName(event.target.value)} required />
                  </label>

                  <label>
                    <span>Username</span>
                    <input value={username} onChange={(event) => setUsername(event.target.value)} required />
                  </label>

                  <label>
                    <span>Password</span>
                    <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
                  </label>
                </div>
              </div>
            )}

            <label className="file-input">
              <span>Source File</span>
              <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
            </label>

            <div className="profile-note">
              <strong>Backend-managed import profiles</strong>
              <p>The backend matches this file against tenant-specific profiles, resolves target models, and prepares the correction loop automatically.</p>
            </div>

            {errorMessage ? <p className="error-banner">{errorMessage}</p> : null}

            <button className="primary-button" type="submit" disabled={submitState === "submitting"}>
              Start Import Job
            </button>
          </form>
        </section>

        <section className="stack">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Live Job</h2>
                <p className="panel-subtitle">Operational detail for the currently selected import job.</p>
              </div>
              <button className="ghost-button" type="button" onClick={() => void refreshJobs()}>
                Refresh
              </button>
            </div>

            {activeJob ? (
              <div className="job-card">
                <div className="job-topline">
                  <strong>{activeJob.original_filename || activeJob.job_id}</strong>
                  <span className={`status-pill status-${activeJob.status}`}>{activeJob.status}</span>
                </div>
                {activeJob.profile_name ? (
                  <div className="profile-badge-row">
                    <span className="profile-badge">Profile: {activeJob.profile_name}</span>
                  </div>
                ) : null}
                <div className="metrics-grid">
                  <div>
                    <span>Total rows</span>
                    <strong>{activeJob.total_rows}</strong>
                  </div>
                  <div>
                    <span>Processed</span>
                    <strong>{activeJob.processed_rows}</strong>
                  </div>
                  <div>
                    <span>Successful</span>
                    <strong>{activeJob.success_rows}</strong>
                  </div>
                  <div>
                    <span>Failed</span>
                    <strong>{activeJob.failed_rows}</strong>
                  </div>
                </div>
                <div className="timeline">
                  <p>Created: {formatDate(activeJob.created_at)}</p>
                  <p>Started: {formatDate(activeJob.started_at)}</p>
                  <p>Completed: {formatDate(activeJob.completed_at)}</p>
                </div>
                {activeJob.error_message ? <p className="error-inline">{activeJob.error_message}</p> : null}
                {activeJob.error_file_url ? (
                  <div className="artifact">
                    <p>Error artifact available for this job.</p>
                    <button className="ghost-button" type="button" onClick={() => void handleDownloadErrorFile()} disabled={downloadState === "downloading"}>
                      {downloadState === "downloading" ? "Downloading..." : "Download Error File"}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="empty-state">No active job selected yet.</p>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Tenant Profiles</h2>
                <p className="panel-subtitle">The ruleset library used to interpret uploaded files.</p>
              </div>
              <span>{profiles.length} available</span>
            </div>

            <div className="profile-list">
              {profiles.length ? (
                profiles.map((profile) => (
                  <div key={profile.name} className="profile-card">
                    <div className="profile-card-topline">
                      <strong>{profile.name}</strong>
                      {profile.is_default ? <span className="status-pill status-completed">Default</span> : null}
                    </div>
                    <p>{profile.description || "No description provided."}</p>
                    {profile.required_headers.length ? <p>Header hints: {profile.required_headers.join(", ")}</p> : null}
                  </div>
                ))
              ) : (
                <p className="empty-state">No profiles configured for this tenant.</p>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Recent Jobs</h2>
                <p className="panel-subtitle">Quick access to recent imports for this tenant.</p>
              </div>
              <span>{jobs.length} loaded</span>
            </div>

            <div className="job-list">
              {jobs.length ? (
                jobs.map((job) => (
                  <button key={job.job_id} className="job-list-item" type="button" onClick={() => setActiveJob(job)}>
                    <div>
                      <strong>{job.original_filename || job.job_id}</strong>
                      <p>{formatDate(job.created_at)}</p>
                    </div>
                    <span className={`status-pill status-${job.status}`}>{job.status}</span>
                  </button>
                ))
              ) : (
                <p className="empty-state">No jobs found for this tenant.</p>
              )}
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
