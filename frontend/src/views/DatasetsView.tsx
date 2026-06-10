import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchDatasets,
  fetchEvaluationJobs,
  fetchImportErrors,
  importDataset,
  createEvaluationJob,
  archiveProject,
  fetchPortkeyProfiles,
  fetchPromptProfiles,
  fetchProjects,
  renameDatasetScan,
  retryFailedEvaluationJob,
  saveProject,
  type Dataset,
  type EvaluationJob,
  type ImportSummary,
} from "../api";
import { Icon } from "../components/Icon";

const ACTIVE_JOB_STATUSES = new Set(["PENDING", "RUNNING", "RETRYING"]);

export function DatasetsView({
  selectedProjectId,
  setSelectedProjectId,
}: {
  selectedProjectId: string;
  setSelectedProjectId: (projectId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [lastImport, setLastImport] = useState<ImportSummary | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [importErrorOffset, setImportErrorOffset] = useState(0);
  const [selectedPortkeyId, setSelectedPortkeyId] = useState("");
  const [selectedPromptId, setSelectedPromptId] = useState("");
  const [uploadMode, setUploadMode] = useState<"default" | "existing" | "new">(
    "default",
  );
  const [newProjectName, setNewProjectName] = useState("");
  const [scanName, setScanName] = useState("");
  const [projectRename, setProjectRename] = useState("");
  const [scanRename, setScanRename] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });
  const datasetsQuery = useQuery({
    queryKey: ["datasets", selectedProjectId],
    queryFn: () => fetchDatasets(selectedProjectId || undefined),
  });
  const evaluationJobsQuery = useQuery({
    queryKey: ["evaluation-jobs", selectedProjectId],
    queryFn: () => fetchEvaluationJobs(selectedProjectId || undefined),
    refetchInterval: (query) => {
      const jobs = query.state.data as EvaluationJob[] | undefined;
      return jobs?.some((job) => ACTIVE_JOB_STATUSES.has(job.status))
        ? 3000
        : false;
    },
  });
  const portkeyQuery = useQuery({
    queryKey: ["portkey-profiles"],
    queryFn: fetchPortkeyProfiles,
  });
  const promptQuery = useQuery({
    queryKey: ["prompt-profiles"],
    queryFn: fetchPromptProfiles,
  });
  const importErrorsQuery = useQuery({
    queryKey: [
      "import-errors",
      selectedDatasetId,
      selectedProjectId,
      importErrorOffset,
    ],
    queryFn: () =>
      fetchImportErrors(
        selectedDatasetId,
        selectedProjectId || undefined,
        importErrorOffset,
      ),
    enabled: selectedDatasetId.length > 0,
  });

  const uploadMutation = useMutation({
    mutationFn: importDataset,
    onSuccess: (summary) => {
      setLastImport(summary);
      setSelectedProjectId(summary.project_id);
      setSelectedDatasetId(summary.dataset_id);
      setScanName("");
      setNewProjectName("");
      void queryClient.invalidateQueries();
    },
  });

  const renameProjectMutation = useMutation({
    mutationFn: () =>
      saveProject({ id: selectedProjectId, name: projectRename.trim() }),
    onSuccess: () => {
      setProjectRename("");
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const archiveProjectMutation = useMutation({
    mutationFn: () => archiveProject(selectedProjectId),
    onSuccess: () => {
      setSelectedProjectId("");
      setSelectedDatasetId("");
      void queryClient.invalidateQueries();
    },
  });

  const renameScanMutation = useMutation({
    mutationFn: () =>
      renameDatasetScan({
        datasetId: selectedDatasetId,
        scanName: scanRename.trim(),
      }),
    onSuccess: () => {
      setScanRename("");
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  const createJobMutation = useMutation({
    mutationFn: () =>
      createEvaluationJob({
        datasetId: selectedDatasetId,
        portkeyProfileId: selectedPortkeyId,
        promptProfileId: selectedPromptId,
        retryLimit: 2,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["evaluation-jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["triage-summary"] });
    },
  });

  const retryJobMutation = useMutation({
    mutationFn: retryFailedEvaluationJob,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["evaluation-jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["triage-summary"] });
    },
  });

  const datasets = datasetsQuery.data ?? [];
  const evaluationJobs = evaluationJobsQuery.data ?? [];
  const projects = projectsQuery.data ?? [];
  const selectedProject = projects.find((p) => p.id === selectedProjectId);
  const datasetsById = new Map(
    datasets.map((dataset) => [dataset.id, dataset]),
  );
  const visibleJobs = evaluationJobs.filter((job) =>
    datasetsById.has(job.dataset_id),
  );
  const projectProgress = summarizeJobs(visibleJobs);
  const scanProgress = datasets
    .map((dataset) => ({
      dataset,
      jobs: visibleJobs.filter((job) => job.dataset_id === dataset.id),
    }))
    .filter((scan) => scan.jobs.length > 0);

  return (
    <div className="view-pad">
      <div className="page-head">
        <h2>Datasets</h2>
        <p>
          Imported red-team exports, normalized into streams and attempts. Raw
          payloads are preserved; metadata is filterable but never recalculated.
        </p>
      </div>

      <div className="card panel-block" style={{ marginBottom: "var(--gap)" }}>
        <h3>
          <Icon name="layers" size={15} /> Project workspace
        </h3>
        <div className="field-row" style={{ marginBottom: 12 }}>
          <div className="field">
            <label>Current project</label>
            <select
              aria-label="Current project"
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                setSelectedDatasetId("");
              }}
            >
              <option value="">All active projects</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name} ({project.import_count} imports)
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Rename project</label>
            <input
              aria-label="Rename project"
              value={projectRename}
              onChange={(e) => setProjectRename(e.target.value)}
              placeholder={selectedProject?.name ?? "Select a project"}
              disabled={!selectedProjectId}
            />
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            className="btn"
            type="button"
            disabled={!selectedProjectId || projectRename.trim().length === 0}
            onClick={() => renameProjectMutation.mutate()}
          >
            <Icon name="check" size={13} /> Rename project
          </button>
          <button
            className="btn"
            type="button"
            disabled={!selectedProjectId || archiveProjectMutation.isPending}
            onClick={() => archiveProjectMutation.mutate()}
          >
            <Icon name="x" size={13} /> Archive project
          </button>
        </div>
        {archiveProjectMutation.error ? (
          <p style={{ color: "var(--threat)", fontSize: 13, marginTop: 8 }}>
            {archiveProjectMutation.error instanceof Error
              ? archiveProjectMutation.error.message
              : "Archive failed"}
          </p>
        ) : null}
      </div>

      <div className="card panel-block" style={{ marginBottom: "var(--gap)" }}>
        <h3>
          <Icon name="download" size={15} /> Upload target
        </h3>
        <div className="field-row">
          <div className="field">
            <label>Project on upload</label>
            <select
              aria-label="Project on upload"
              value={uploadMode}
              onChange={(e) =>
                setUploadMode(e.target.value as "default" | "existing" | "new")
              }
            >
              <option value="default">Default from filename</option>
              <option value="existing">Attach to current project</option>
              <option value="new">Create new project</option>
            </select>
          </div>
          <div className="field">
            <label>New project name</label>
            <input
              aria-label="New project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              disabled={uploadMode !== "new"}
            />
          </div>
          <div className="field">
            <label>Scan name</label>
            <input
              aria-label="Scan name"
              value={scanName}
              onChange={(e) => setScanName(e.target.value)}
              placeholder="Default from filename"
            />
          </div>
        </div>
      </div>

      <label
        className="dropzone"
        style={{
          marginBottom: "var(--gap)",
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <input
          aria-label="Upload red-team export"
          name="red-team-export"
          type="file"
          accept=".json,.csv,application/json,text/csv"
          disabled={
            (uploadMode === "existing" && !selectedProjectId) ||
            (uploadMode === "new" && newProjectName.trim().length === 0)
          }
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              uploadMutation.mutate({
                file,
                projectId:
                  uploadMode === "existing" ? selectedProjectId : undefined,
                projectName:
                  uploadMode === "new" ? newProjectName.trim() : undefined,
                scanName: scanName.trim() || undefined,
              });
            }
          }}
        />
        <div className="dz-ic">
          <Icon name="download" size={20} />
        </div>
        <strong>Drop a CSV or JSON export to import</strong>
        <p>
          Static (prompt · output · threat) and agent (goal · stream_id ·
          iteration_N) shapes are auto-detected.
        </p>
      </label>

      {uploadMutation.isPending ? <p className="muted">Importing...</p> : null}
      {uploadMutation.error ? (
        <p style={{ color: "var(--threat)", fontSize: 13 }}>
          {uploadMutation.error instanceof Error
            ? uploadMutation.error.message
            : "Import failed"}
        </p>
      ) : null}
      {lastImport ? (
        <div
          className="card panel-block"
          aria-label="Import summary"
          style={{ marginBottom: "var(--gap)" }}
        >
          <h3>
            <Icon name="checkCircle" size={15} /> Import complete
          </h3>
          <p className="sub">
            {lastImport.scan_name} · {lastImport.detected_format} ·{" "}
            {lastImport.imported_count} imported · {lastImport.error_count}{" "}
            errors · {lastImport.status}
          </p>
        </div>
      ) : null}

      {datasets.length > 0 ? (
        <div
          className="card"
          style={{ overflow: "hidden", marginBottom: "var(--gap)" }}
        >
          <table className="simple-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Scan</th>
                <th>Format</th>
                <th>Streams</th>
                <th>Attempts</th>
                <th>Errors</th>
                <th>Parser</th>
                <th>Imported</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td>
                    <span className="mono" style={{ fontSize: 12.5 }}>
                      {d.source_filename ?? d.id}
                    </span>
                  </td>
                  <td>{d.scan_name}</td>
                  <td>
                    <span className="tag">{d.detected_format}</span>
                  </td>
                  <td className="mono">{d.stream_count}</td>
                  <td className="mono">{d.attempt_count}</td>
                  <td
                    className="mono"
                    style={{
                      color: d.error_count ? "var(--error)" : "var(--ink-3)",
                    }}
                  >
                    {d.error_count}
                  </td>
                  <td>
                    <span className="hash-pill">{d.parser_version}</span>
                  </td>
                  <td className="muted">{d.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <EvaluationProgressPanel
        loading={evaluationJobsQuery.isLoading}
        projectProgress={projectProgress}
        scanProgress={scanProgress}
        retryingJobId={retryJobMutation.variables ?? null}
        retryPending={retryJobMutation.isPending}
        onRetry={(jobId) => retryJobMutation.mutate(jobId)}
      />

      <div className="card panel-block">
        <h3>
          <Icon name="play" size={15} /> Run evaluation
        </h3>
        <p className="sub">
          Select a dataset, Portkey profile, and prompt profile to start a Judge
          evaluation job.
        </p>
        <div className="field-row" style={{ marginBottom: 14 }}>
          <div className="field">
            <label>Dataset</label>
            <select
              aria-label="Dataset"
              name="diagnostics-dataset"
              value={selectedDatasetId}
              onChange={(e) => {
                setSelectedDatasetId(e.target.value);
                setImportErrorOffset(0);
              }}
            >
              <option value="">Select dataset</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.scan_name} ({d.error_count} errors)
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Portkey profile</label>
            <select
              aria-label="Portkey profile"
              name="portkey-profile"
              value={selectedPortkeyId}
              onChange={(e) => setSelectedPortkeyId(e.target.value)}
            >
              <option value="">Select profile</option>
              {(portkeyQuery.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.profile_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field" style={{ maxWidth: 320 }}>
          <label>Prompt profile</label>
          <select
            aria-label="Prompt profile"
            name="prompt-profile"
            value={selectedPromptId}
            onChange={(e) => setSelectedPromptId(e.target.value)}
          >
            <option value="">Select prompt</option>
            {(promptQuery.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} {p.is_default ? "(default)" : ""}
              </option>
            ))}
          </select>
        </div>
        <button
          className="btn primary"
          type="button"
          onClick={() => createJobMutation.mutate()}
          disabled={
            !selectedDatasetId ||
            !selectedPortkeyId ||
            !selectedPromptId ||
            createJobMutation.isPending
          }
        >
          <Icon name="play" size={14} /> Run evaluation
        </button>
        {createJobMutation.data ? (
          <p
            style={{
              color: "var(--safe)",
              fontSize: 13,
              fontWeight: 600,
              marginTop: 8,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Icon name="checkCircle" size={16} /> Job{" "}
            {createJobMutation.data.status} with{" "}
            {createJobMutation.data.total_attempts} attempts
          </p>
        ) : null}
        {createJobMutation.error ? (
          <p style={{ color: "var(--threat)", fontSize: 13, marginTop: 8 }}>
            {createJobMutation.error instanceof Error
              ? createJobMutation.error.message
              : "Job creation failed"}
          </p>
        ) : null}
      </div>

      {selectedDatasetId ? (
        <div
          className="card panel-block"
          style={{ marginTop: "var(--gap)" }}
          aria-label="Import error menu"
        >
          <h3>
            <Icon name="alert" size={15} /> Import errors
          </h3>
          <p className="sub">Parsing errors for the selected dataset.</p>
          <div className="field-row" style={{ marginBottom: 12 }}>
            <div className="field">
              <label>Rename scan</label>
              <input
                aria-label="Rename scan"
                value={scanRename}
                onChange={(e) => setScanRename(e.target.value)}
                placeholder="New scan name"
              />
            </div>
            <button
              className="btn"
              type="button"
              disabled={scanRename.trim().length === 0}
              onClick={() => renameScanMutation.mutate()}
              style={{ alignSelf: "end" }}
            >
              <Icon name="check" size={13} /> Rename scan
            </button>
          </div>
          {(importErrorsQuery.data ?? []).length === 0 ? (
            <p className="muted" style={{ fontSize: 13 }}>
              No import errors for the selected dataset.
            </p>
          ) : (
            <div className="import-error-list">
              {(importErrorsQuery.data ?? []).map((err) => (
                <div key={err.id} className="import-error-item">
                  <strong>{err.error_code}</strong>
                  <span
                    className="muted"
                    style={{ marginLeft: 8, fontSize: 11.5 }}
                  >
                    Record {err.record_index ?? "-"}
                  </span>
                  <p>{err.message}</p>
                  {err.raw_payload ? (
                    <pre>{JSON.stringify(err.raw_payload, null, 2)}</pre>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          <div className="pagination-row">
            <button
              className="btn sm"
              type="button"
              onClick={() =>
                setImportErrorOffset(Math.max(importErrorOffset - 25, 0))
              }
              disabled={importErrorOffset === 0}
            >
              Previous
            </button>
            <span>Offset {importErrorOffset}</span>
            <button
              className="btn sm"
              type="button"
              onClick={() => setImportErrorOffset(importErrorOffset + 25)}
              disabled={(importErrorsQuery.data ?? []).length < 25}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function EvaluationProgressPanel({
  loading,
  projectProgress,
  scanProgress,
  retryingJobId,
  retryPending,
  onRetry,
}: {
  loading: boolean;
  projectProgress: ProgressSummary;
  scanProgress: Array<{ dataset: Dataset; jobs: EvaluationJob[] }>;
  retryingJobId: string | null;
  retryPending: boolean;
  onRetry: (jobId: string) => void;
}) {
  return (
    <div
      className="card panel-block evaluation-progress"
      style={{ marginBottom: "var(--gap)" }}
      aria-label="Evaluation progress"
    >
      <h3>
        <Icon name="clock" size={15} /> Evaluation progress
      </h3>
      <p className="sub">
        Judge job progress across the visible scans in the current project view.
      </p>

      {loading ? <p className="muted">Loading evaluation progress...</p> : null}
      {!loading && scanProgress.length === 0 ? (
        <p className="muted">No evaluation jobs for the visible scans.</p>
      ) : null}

      {scanProgress.length > 0 ? (
        <>
          <div
            className="progress-summary"
            aria-label="Project evaluation rollup"
          >
            <div>
              <span className="progress-label">Project rollup</span>
              <strong>
                {projectProgress.processed} / {projectProgress.total} processed
              </strong>
            </div>
            <ProgressBar summary={projectProgress} />
            <div className="progress-counts">
              <span>{projectProgress.succeeded} succeeded</span>
              <span>{projectProgress.failed} failed</span>
              <span>{projectProgress.remaining} remaining</span>
            </div>
          </div>

          <div className="scan-progress-list">
            {scanProgress.map(({ dataset, jobs }) => (
              <div className="scan-progress" key={dataset.id}>
                <div className="scan-progress-head">
                  <div>
                    <span className="progress-label">Scan</span>
                    <strong>{dataset.scan_name}</strong>
                  </div>
                  <span className="muted">{jobs.length} job(s)</span>
                </div>
                {jobs.map((job) => {
                  const summary = summarizeJobs([job]);
                  return (
                    <div className="job-progress" key={job.id}>
                      <div className="job-progress-main">
                        <StatusBadge status={job.status} />
                        <span className="mono">
                          {summary.processed} / {summary.total}
                        </span>
                        <span>{summary.succeeded} succeeded</span>
                        <span>{summary.failed} failed</span>
                        <span>{summary.remaining} remaining</span>
                      </div>
                      <ProgressBar summary={summary} />
                      <div className="job-progress-foot">
                        <span className="muted">
                          Created {job.created_at.slice(0, 10)}
                        </span>
                        {job.status === "FAILED" && job.failed_attempts > 0 ? (
                          <button
                            className="btn sm"
                            type="button"
                            disabled={retryPending && retryingJobId === job.id}
                            onClick={() => onRetry(job.id)}
                          >
                            <Icon name="refresh" size={13} /> Retry failed
                          </button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`job-status ${status.toLowerCase()}`}>{status}</span>;
}

function ProgressBar({ summary }: { summary: ProgressSummary }) {
  return (
    <div
      className={`progress-bar ${summary.statusClass}`}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={summary.total}
      aria-valuenow={summary.processed}
    >
      <span style={{ width: `${summary.percent}%` }} />
    </div>
  );
}

type ProgressSummary = {
  total: number;
  processed: number;
  succeeded: number;
  failed: number;
  remaining: number;
  percent: number;
  statusClass: "active" | "completed" | "failed" | "empty";
};

function summarizeJobs(jobs: EvaluationJob[]): ProgressSummary {
  const total = jobs.reduce((sum, job) => sum + job.total_attempts, 0);
  const processed = jobs.reduce((sum, job) => sum + job.processed_attempts, 0);
  const succeeded = jobs.reduce((sum, job) => sum + job.succeeded_attempts, 0);
  const failed = jobs.reduce((sum, job) => sum + job.failed_attempts, 0);
  const remaining = Math.max(total - processed, 0);
  const percent = total > 0 ? Math.round((processed / total) * 100) : 0;
  const hasActive = jobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));
  const hasFailed = jobs.some((job) => job.status === "FAILED");
  const allCompleted =
    jobs.length > 0 && jobs.every((job) => job.status === "COMPLETED");
  return {
    total,
    processed,
    succeeded,
    failed,
    remaining,
    percent,
    statusClass: hasActive
      ? "active"
      : hasFailed
        ? "failed"
        : allCompleted
          ? "completed"
          : "empty",
  };
}
