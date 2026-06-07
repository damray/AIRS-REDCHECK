import { useQuery } from "@tanstack/react-query";

import { fetchTriageSummary, type AutomatedTriageSummary } from "../api";
import { Donut } from "../components/Donut";
import { Icon } from "../components/Icon";
import { STATUS_META } from "../components/StatusPill";

const pct = (v: number | null) => (v == null ? "—" : Math.round(v * 100) + "%");

export function TriageView({
  goReview,
  goReviewFiltered,
  pendingCount,
}: {
  goReview: () => void;
  goReviewFiltered: (statuses: string[]) => void;
  pendingCount: number;
}) {
  const triageQuery = useQuery({
    queryKey: ["triage-summary"],
    queryFn: fetchTriageSummary,
  });

  const t: AutomatedTriageSummary = triageQuery.data ?? {
    total_streams: 0,
    total_attempts: 0,
    processed_attempts: 0,
    remaining_attempts: 0,
    errors: 0,
    agreements: 0,
    disagreements: 0,
    source_stricter_than_judge: 0,
    judge_stricter_than_source: 0,
    uncertain: 0,
    review_required: 0,
    agent_streams: 0,
    static_streams: 0,
    average_attempts_per_stream: 0,
  };

  const procPct = t.total_attempts
    ? t.processed_attempts / t.total_attempts
    : 0;

  const breakdown = [
    {
      key: "SOURCE_STRICTER_THAN_JUDGE",
      color: "var(--uncertain)",
      count: t.source_stricter_than_judge,
    },
    {
      key: "JUDGE_STRICTER_THAN_SOURCE",
      color: "var(--threat)",
      count: t.judge_stricter_than_source,
    },
    {
      key: "REVIEW_REQUIRED",
      color: "var(--accent)",
      count: t.review_required,
    },
    {
      key: "AGREEMENT_THREAT",
      color: "var(--safe)",
      count: Math.max(
        0,
        t.agreements -
          (t.total_attempts -
            t.source_stricter_than_judge -
            t.judge_stricter_than_source -
            t.review_required -
            t.errors -
            t.agreements),
      ),
    },
    { key: "AGREEMENT_SAFE", color: "var(--safe)", count: 0 },
    { key: "EVALUATION_ERROR", color: "var(--error)", count: t.errors },
  ];

  const donutSegs = [
    { label: "Agreements", value: t.agreements, color: "var(--safe)" },
    {
      label: "Disagreements",
      value: t.disagreements,
      color: "var(--uncertain)",
    },
    { label: "Errors", value: t.errors, color: "var(--error)" },
  ];

  return (
    <div className="view-pad" aria-label="Dashboard summaries">
      <div className="page-head">
        <div className="page-head-row">
          <div>
            <h2>Triage overview</h2>
            <p>
              Automated comparison of the source evaluator against the blind
              Judge across imported red-team responses. The Judge is not ground
              truth — only human adjudication confirms verdicts.
            </p>
          </div>
        </div>
      </div>

      {pendingCount > 0 ? (
        <div className="cta-banner">
          <div className="cb-ic">
            <Icon name="scale" size={20} />
          </div>
          <div className="cb-txt">
            <strong>
              {pendingCount} disagreement{pendingCount === 1 ? "" : "s"}{" "}
              awaiting adjudication
            </strong>
            <p>
              Source and Judge disagree, or the Judge was uncertain. These need
              a human verdict before they count toward quality metrics.
            </p>
          </div>
          <button className="btn primary" type="button" onClick={goReview}>
            Open review queue <Icon name="arrowRight" size={15} />
          </button>
        </div>
      ) : null}

      {triageQuery.isLoading ? (
        <p className="muted">Loading triage data...</p>
      ) : null}

      <div className="kpi-row">
        <div className="card kpi">
          <span className="kpi-label">
            <Icon name="layers" size={14} /> Streams
          </span>
          <span className="kpi-val">{t.total_streams}</span>
          <span className="kpi-sub">
            {t.agent_streams} agent · {t.static_streams} static
          </span>
        </div>
        <div className="card kpi">
          <span className="kpi-label">
            <Icon name="inbox" size={14} /> Attempts
          </span>
          <span className="kpi-val">{t.total_attempts}</span>
          <span className="kpi-sub">
            {t.average_attempts_per_stream.toFixed(1)} avg per stream
          </span>
        </div>
        <div className="card kpi accent">
          <span className="kpi-label">
            <Icon name="alert" size={14} /> Disagreements
          </span>
          <span className="kpi-val">
            {t.disagreements}
            <span className="unit">/ {t.processed_attempts}</span>
          </span>
          <span className="kpi-sub">
            {pct(
              t.processed_attempts ? t.disagreements / t.processed_attempts : 0,
            )}{" "}
            of processed
          </span>
        </div>
        <div className="card kpi">
          <span className="kpi-label">
            <Icon name="bolt" size={14} /> Eval errors
          </span>
          <span
            className="kpi-val"
            style={{ color: t.errors ? "var(--error)" : undefined }}
          >
            {t.errors}
          </span>
          <span className="kpi-sub">
            {t.errors ? (
              <button
                className="btn ghost sm"
                type="button"
                style={{ padding: 0, color: "var(--error)" }}
                onClick={() => goReviewFiltered(["EVALUATION_ERROR"])}
                aria-label="View evaluation errors"
              >
                View failures →
              </button>
            ) : (
              "none"
            )}
          </span>
        </div>
      </div>

      <div className="dash-grid">
        <div className="card panel-block">
          <h3>
            <Icon name="filter" size={15} /> Comparison breakdown
          </h3>
          <p className="sub">
            Click a category to open it in the review queue.
          </p>
          <div className="breakdown">
            {breakdown.map((b) => {
              const meta = STATUS_META[b.key];
              if (!meta) return null;
              return (
                <div
                  className="breakdown-row"
                  key={b.key}
                  onClick={() => goReviewFiltered([b.key])}
                >
                  <span className="bd-swatch" style={{ background: b.color }} />
                  <div className="bd-key">
                    <div className="bd-name">{meta.label}</div>
                    <div className="bd-implies">{meta.implies}</div>
                  </div>
                  <span className="bd-count">{b.count}</span>
                  <span className="bd-share">
                    {pct(t.total_attempts ? b.count / t.total_attempts : 0)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--gap)",
          }}
        >
          <div className="card panel-block">
            <h3>
              <Icon name="gauge" size={15} /> Processing
            </h3>
            <p className="sub">Attempts evaluated by the Judge.</p>
            <div className="funnel">
              <div className="funnel-row">
                <div className="ft">
                  <span className="fl">Processed</span>
                  <span className="fv">
                    {t.processed_attempts} / {t.total_attempts}
                  </span>
                </div>
                <div className="bar">
                  <span
                    style={{
                      width: `${procPct * 100}%`,
                      background: "var(--accent)",
                    }}
                  />
                </div>
              </div>
              <div className="funnel-row">
                <div className="ft">
                  <span className="fl">Agreements</span>
                  <span className="fv">{t.agreements}</span>
                </div>
                <div className="bar">
                  <span
                    style={{
                      width: `${(t.agreements / (t.total_attempts || 1)) * 100}%`,
                      background: "var(--safe)",
                    }}
                  />
                </div>
              </div>
              <div className="funnel-row">
                <div className="ft">
                  <span className="fl">Disagreements</span>
                  <span className="fv">{t.disagreements}</span>
                </div>
                <div className="bar">
                  <span
                    style={{
                      width: `${(t.disagreements / (t.total_attempts || 1)) * 100}%`,
                      background: "var(--uncertain)",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card panel-block">
            <h3>
              <Icon name="target" size={15} /> Outcome mix
            </h3>
            <div className="donut-wrap" style={{ marginTop: 12 }}>
              <Donut
                segments={donutSegs}
                size={124}
                thickness={20}
                centerLabel={t.total_attempts}
                centerSub="attempts"
              />
              <div className="donut-legend">
                {donutSegs.map((s) => (
                  <div className="dl" key={s.label}>
                    <span className="dlc" style={{ background: s.color }} />
                    <span className="dln">{s.label}</span>
                    <span className="dlv">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
