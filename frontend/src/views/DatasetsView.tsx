import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchDatasets,
  fetchImportErrors,
  importDataset,
  createEvaluationJob,
  fetchPortkeyProfiles,
  fetchPromptProfiles,
  type ImportSummary,
} from "../api";
import { Icon } from "../components/Icon";

export function DatasetsView() {
  const queryClient = useQueryClient();
  const [lastImport, setLastImport] = useState<ImportSummary | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [importErrorOffset, setImportErrorOffset] = useState(0);
  const [selectedPortkeyId, setSelectedPortkeyId] = useState("");
  const [selectedPromptId, setSelectedPromptId] = useState("");

  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: fetchDatasets,
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
    queryKey: ["import-errors", selectedDatasetId, importErrorOffset],
    queryFn: () => fetchImportErrors(selectedDatasetId, importErrorOffset),
    enabled: selectedDatasetId.length > 0,
  });

  const uploadMutation = useMutation({
    mutationFn: importDataset,
    onSuccess: (summary) => {
      setLastImport(summary);
      setSelectedDatasetId(summary.dataset_id);
      void queryClient.invalidateQueries();
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
      void queryClient.invalidateQueries({ queryKey: ["triage-summary"] });
    },
  });

  const datasets = datasetsQuery.data ?? [];

  return (
    <div className="view-pad">
      <div className="page-head">
        <h2>Datasets</h2>
        <p>
          Imported red-team exports, normalized into streams and attempts. Raw
          payloads are preserved; metadata is filterable but never recalculated.
        </p>
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
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadMutation.mutate(file);
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
            {lastImport.detected_format} · {lastImport.imported_count} imported
            · {lastImport.error_count} errors · {lastImport.status}
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
                  {d.source_filename ?? d.id} ({d.error_count} errors)
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
