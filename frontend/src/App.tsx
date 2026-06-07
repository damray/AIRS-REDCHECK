import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  defaultDisagreementFilters,
  fetchResults,
  resetImportedDatasets,
} from "./api";
import { Icon } from "./components/Icon";
import { ConfigView } from "./views/ConfigView";
import { DatasetsView } from "./views/DatasetsView";
import { ExportView } from "./views/ExportView";
import { QualityView } from "./views/QualityView";
import { ReviewView } from "./views/ReviewView";
import { TriageView } from "./views/TriageView";

type ViewId =
  | "triage"
  | "review"
  | "quality"
  | "export"
  | "datasets"
  | "config";

const NAV: Array<{ id: ViewId; label: string; icon: string }> = [
  { id: "triage", label: "Triage", icon: "gauge" },
  { id: "review", label: "Review", icon: "scale" },
  { id: "quality", label: "Quality", icon: "target" },
  { id: "export", label: "Export", icon: "download" },
];
const NAV2: Array<{ id: ViewId; label: string; icon: string }> = [
  { id: "datasets", label: "Datasets", icon: "database" },
  { id: "config", label: "Judge config", icon: "sliders" },
];

const CRUMB: Record<ViewId, string> = {
  triage: "Triage overview",
  review: "Disagreement review",
  quality: "Reviewed quality",
  export: "Export results",
  datasets: "Datasets",
  config: "Judge configuration",
};

export function App() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<ViewId>("review");
  const [dark, setDark] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [reviewer, setReviewer] = useState("analyst");
  const [reviewFilter, setReviewFilter] = useState<string[]>(
    defaultDisagreementFilters().comparisonStatus,
  );

  const pendingQuery = useQuery({
    queryKey: [
      "results",
      {
        comparisonStatus: [
          "SOURCE_STRICTER_THAN_JUDGE",
          "JUDGE_STRICTER_THAN_SOURCE",
          "REVIEW_REQUIRED",
        ],
        sourceVerdict: "",
        judgeVerdict: "",
        inputType: "",
        reviewed: "false",
        contextContains: "",
        outputContains: "",
      },
      0,
    ],
    queryFn: () =>
      fetchResults(
        {
          ...defaultDisagreementFilters(),
          reviewed: "false",
        },
        0,
        1,
      ),
  });
  const pendingCount = pendingQuery.data?.total ?? 0;

  function goReview() {
    setReviewFilter([
      "SOURCE_STRICTER_THAN_JUDGE",
      "JUDGE_STRICTER_THAN_SOURCE",
      "REVIEW_REQUIRED",
    ]);
    setView("review");
  }

  function goReviewFiltered(statuses: string[]) {
    setReviewFilter(statuses);
    setView("review");
  }

  return (
    <div
      className={dark ? "theme-dark" : "theme-light"}
      style={{ height: "100%" }}
    >
      <div className={`app${navCollapsed ? " nav-collapsed" : ""}`}>
        {/* sidebar */}
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">
              <Icon name="shieldCheck" size={18} />
            </div>
            <div className="brand-name">
              AIRS Redcheck<small>Threat evaluator</small>
            </div>
          </div>
          {NAV.map((n) => (
            <NavBtn
              key={n.id}
              item={n}
              active={view === n.id}
              onClick={() => setView(n.id)}
              count={
                n.id === "review" && pendingCount > 0 ? pendingCount : undefined
              }
            />
          ))}
          <div className="nav-section-label">Manage</div>
          {NAV2.map((n) => (
            <NavBtn
              key={n.id}
              item={n}
              active={view === n.id}
              onClick={() => setView(n.id)}
            />
          ))}
          <div className="sidebar-foot">
            <button
              className="nav-item"
              type="button"
              onClick={() => setNavCollapsed((c) => !c)}
              title="Collapse"
            >
              <span className="nav-icon">
                <Icon
                  name={navCollapsed ? "chevronRight" : "chevronsLeft"}
                  size={18}
                />
              </span>
              <span className="nav-label">Collapse</span>
            </button>
          </div>
        </aside>

        {/* main */}
        <div className="main">
          <header className="topbar">
            <h1>{CRUMB[view]}</h1>
            <span className="topbar-spacer" />
            <button
              className="iconbtn"
              type="button"
              title="Refresh data"
              aria-label="Refresh data"
              onClick={() => void queryClient.invalidateQueries()}
            >
              <Icon name="refresh" size={16} />
            </button>
            <button
              className="iconbtn"
              type="button"
              title="Toggle theme"
              onClick={() => setDark((d) => !d)}
            >
              <Icon name={dark ? "sun" : "moon"} size={16} />
            </button>
          </header>

          <div className="view" key={view}>
            {view === "triage" ? (
              <TriageView
                goReview={goReview}
                goReviewFiltered={goReviewFiltered}
                pendingCount={pendingCount}
              />
            ) : null}
            {view === "review" ? (
              <ReviewView
                initialFilter={reviewFilter}
                reviewer={reviewer}
                setReviewer={setReviewer}
              />
            ) : null}
            {view === "quality" ? <QualityView goReview={goReview} /> : null}
            {view === "export" ? <ExportView /> : null}
            {view === "datasets" ? <DatasetsView /> : null}
            {view === "config" ? <ConfigView /> : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function NavBtn({
  item,
  active,
  onClick,
  count,
}: {
  item: { id: string; label: string; icon: string };
  active: boolean;
  onClick: () => void;
  count?: number;
}) {
  return (
    <button
      className={`nav-item${active ? " active" : ""}`}
      type="button"
      onClick={onClick}
      title={item.label}
    >
      <span className="nav-icon">
        <Icon name={item.icon} size={18} />
      </span>
      <span className="nav-label">{item.label}</span>
      {count !== undefined ? (
        <span className="nav-count alert">{count}</span>
      ) : null}
    </button>
  );
}
