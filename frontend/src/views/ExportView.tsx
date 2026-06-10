import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  defaultDisagreementFilters,
  fetchResults,
  filteredExportUrl,
  type ResultFilters,
} from "../api";
import { Icon } from "../components/Icon";

const STATUS_FILTERS = [
  { key: "SOURCE_STRICTER_THAN_JUDGE", short: "Source stricter" },
  { key: "JUDGE_STRICTER_THAN_SOURCE", short: "Judge stricter" },
  { key: "REVIEW_REQUIRED", short: "Review required" },
  { key: "AGREEMENT_THREAT", short: "Agree · threat" },
  { key: "AGREEMENT_SAFE", short: "Agree · safe" },
  { key: "EVALUATION_ERROR", short: "Errors" },
];

const PRESETS = [
  {
    title: "Normalized results",
    icon: "layers",
    description:
      "All imported attempts with source and Judge verdicts, comparison status, and review decisions. No filters applied.",
    href: "/api/results/export/normalized.csv",
    filename: "airs-redcheck-normalized-results.csv",
  },
  {
    title: "Disagreements only",
    icon: "alert",
    description:
      "Attempts where source and Judge disagree, or the Judge was uncertain. Includes source-stricter, judge-stricter, and review-required statuses.",
    href: "/api/results/export/disagreements.csv",
    filename: "airs-redcheck-disagreements.csv",
  },
  {
    title: "Reviewed cases",
    icon: "checkCircle",
    description:
      "Only human-adjudicated attempts. Includes the reviewer, decision, comment, and timestamp for each reviewed case.",
    href: "/api/results/export/reviewed.csv",
    filename: "airs-redcheck-reviewed-cases.csv",
  },
];

function emptyFilters(): ResultFilters {
  return {
    comparisonStatus: [],
    sourceVerdict: "",
    judgeVerdict: "",
    inputType: "",
    reviewed: "",
    contextContains: "",
    outputContains: "",
  };
}

export function ExportView({ projectId }: { projectId?: string }) {
  const [filters, setFilters] = useState<ResultFilters>(emptyFilters);

  const hasFilters =
    filters.comparisonStatus.length > 0 ||
    filters.sourceVerdict !== "" ||
    filters.judgeVerdict !== "" ||
    filters.inputType !== "" ||
    filters.reviewed !== "" ||
    filters.contextContains.trim() !== "" ||
    filters.outputContains.trim() !== "";

  const countQuery = useQuery({
    queryKey: ["export-preview", filters, projectId ?? ""],
    queryFn: () => fetchResults(filters, 0, 1, projectId),
  });

  const matchCount = countQuery.data?.total ?? null;
  const exportUrl = filteredExportUrl(filters, projectId);
  const projectQuery = projectId
    ? `?project_id=${encodeURIComponent(projectId)}`
    : "";

  function toggleStatus(key: string) {
    setFilters((f) => ({
      ...f,
      comparisonStatus: f.comparisonStatus.includes(key)
        ? f.comparisonStatus.filter((s) => s !== key)
        : [...f.comparisonStatus, key],
    }));
  }

  return (
    <div className="view-pad">
      <div className="page-head">
        <h2>Export results</h2>
        <p>
          Download evaluation results as CSV. Use a quick preset or build a
          custom filtered export with the same filters available in the result
          explorer.
        </p>
      </div>

      {/* Presets */}
      <div className="export-presets">
        {PRESETS.map((p) => (
          <div className="card panel-block export-preset-card" key={p.title}>
            <div className="export-preset-icon">
              <Icon name={p.icon} size={20} />
            </div>
            <h3>{p.title}</h3>
            <p className="sub">{p.description}</p>
            <a
              className="btn primary"
              href={`${p.href}${projectQuery}`}
              download={p.filename}
              style={{ textDecoration: "none", marginTop: "auto" }}
            >
              <Icon name="download" size={14} /> Download CSV
            </a>
          </div>
        ))}
      </div>

      {/* Custom filtered export */}
      <div className="card panel-block" style={{ marginTop: "var(--gap)" }}>
        <h3>
          <Icon name="filter" size={15} /> Custom filtered export
        </h3>
        <p className="sub">
          Combine filters to export a specific working set — e.g. all agreed
          threats, all reviewed high-severity disagreements, or a text-search
          subset.
        </p>

        {/* Comparison status chips */}
        <div style={{ marginBottom: 14 }}>
          <label
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--ink-2)",
              display: "block",
              marginBottom: 8,
            }}
          >
            Comparison status
          </label>
          <div className="filter-chips">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                className={`fchip${filters.comparisonStatus.includes(f.key) ? " active" : ""}`}
                onClick={() => toggleStatus(f.key)}
              >
                {f.short}
              </button>
            ))}
          </div>
        </div>

        {/* Dropdowns row */}
        <div className="export-filter-grid">
          <div className="field">
            <label>Source verdict</label>
            <select
              value={filters.sourceVerdict}
              onChange={(e) =>
                setFilters({ ...filters, sourceVerdict: e.target.value })
              }
            >
              <option value="">Any</option>
              <option value="THREAT">Threat</option>
              <option value="SAFE">Safe</option>
            </select>
          </div>
          <div className="field">
            <label>Judge verdict</label>
            <select
              value={filters.judgeVerdict}
              onChange={(e) =>
                setFilters({ ...filters, judgeVerdict: e.target.value })
              }
            >
              <option value="">Any</option>
              <option value="THREAT">Threat</option>
              <option value="SAFE">Safe</option>
              <option value="UNCERTAIN">Uncertain</option>
            </select>
          </div>
          <div className="field">
            <label>Input type</label>
            <select
              value={filters.inputType}
              onChange={(e) =>
                setFilters({ ...filters, inputType: e.target.value })
              }
            >
              <option value="">Any</option>
              <option value="agent">Agent</option>
              <option value="static">Static</option>
            </select>
          </div>
          <div className="field">
            <label>Reviewed</label>
            <select
              value={filters.reviewed}
              onChange={(e) =>
                setFilters({ ...filters, reviewed: e.target.value })
              }
            >
              <option value="">Any</option>
              <option value="true">Reviewed</option>
              <option value="false">Not reviewed</option>
            </select>
          </div>
        </div>

        {/* Text search */}
        <div className="export-filter-grid" style={{ marginBottom: 18 }}>
          <div className="field" style={{ gridColumn: "span 2" }}>
            <label>Prompt or output contains</label>
            <input
              value={filters.contextContains}
              onChange={(e) =>
                setFilters({ ...filters, contextContains: e.target.value })
              }
              placeholder="Search across prompt and output text…"
            />
          </div>
          <div className="field" style={{ gridColumn: "span 2" }}>
            <label>Output contains</label>
            <input
              value={filters.outputContains}
              onChange={(e) =>
                setFilters({ ...filters, outputContains: e.target.value })
              }
              placeholder="Filter by output text only…"
            />
          </div>
        </div>

        {/* Result count + actions */}
        <div className="export-actions-row">
          <div className="export-count">
            {countQuery.isLoading ? (
              <span className="muted">Counting…</span>
            ) : matchCount !== null ? (
              <span>
                <strong className="mono">{matchCount}</strong>{" "}
                <span className="muted">
                  result{matchCount === 1 ? "" : "s"} match
                  {hasFilters
                    ? " current filters"
                    : " (no filters — all results)"}
                </span>
              </span>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {hasFilters ? (
              <button
                className="btn"
                type="button"
                onClick={() => setFilters(emptyFilters())}
              >
                <Icon name="x" size={13} /> Reset filters
              </button>
            ) : null}
            <a
              className={`btn primary${matchCount === 0 ? " disabled" : ""}`}
              href={exportUrl}
              download="airs-redcheck-filtered-results.csv"
              style={{
                textDecoration: "none",
                pointerEvents: matchCount === 0 ? "none" : undefined,
                opacity: matchCount === 0 ? 0.45 : undefined,
              }}
            >
              <Icon name="download" size={14} /> Export filtered CSV
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
