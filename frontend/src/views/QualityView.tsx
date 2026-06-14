import { useQuery } from "@tanstack/react-query";

import { fetchReviewedQuality } from "../api";
import { Icon } from "../components/Icon";
import { Ring } from "../components/Ring";

const pct = (v: number | null | undefined) =>
  v == null ? "—" : Math.round(v * 100) + "%";

export function QualityView({
  goReview,
  projectId,
}: {
  goReview: () => void;
  projectId?: string;
}) {
  const qualityQuery = useQuery({
    queryKey: ["reviewed-quality", projectId ?? ""],
    queryFn: () => fetchReviewedQuality(projectId),
  });

  const q = qualityQuery.data;

  if (qualityQuery.isLoading) {
    return (
      <div className="view-pad">
        <p className="muted">Loading quality metrics...</p>
      </div>
    );
  }

  if (!q) return null;

  const metrics = [
    { l: "Accuracy", v: q.accuracy },
    { l: "Precision", v: q.precision },
    { l: "Recall", v: q.recall },
    { l: "F1 score", v: q.f1_score },
  ];

  return (
    <div className="view-pad">
      <div className="page-head">
        <h2>Reviewed quality</h2>
        <p>
          Metrics computed <strong>only</strong> from human-adjudicated cases.
          The confirmed verdict is treated as ground truth and the{" "}
          <em>source evaluator</em> is scored against it. Alarm threat reviews
          count as low-impact threat verdicts.
        </p>
      </div>

      {q.metric_cases === 0 ? (
        <div
          className="card panel-block"
          style={{ textAlign: "center", padding: "48px 24px" }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 13,
              background: "var(--surface-3)",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 14px",
              color: "var(--ink-3)",
            }}
          >
            <Icon name="target" size={24} />
          </div>
          <strong style={{ fontSize: 15 }}>No adjudicated cases yet</strong>
          <p className="muted" style={{ margin: "6px 0 16px", fontSize: 13 }}>
            Confirm or reject verdicts in the review queue to populate the
            confusion matrix.
          </p>
          <button
            className="btn primary"
            type="button"
            onClick={goReview}
            style={{ margin: "0 auto" }}
          >
            Go to review <Icon name="arrowRight" size={15} />
          </button>
        </div>
      ) : (
        <div className="quality-grid">
          <div className="card panel-block">
            <h3>
              <Icon name="layers" size={15} /> Confusion matrix
            </h3>
            <p className="sub">
              Source verdict vs. confirmed ground truth · {q.metric_cases} case
              {q.metric_cases === 1 ? "" : "s"}
            </p>
            <div className="confusion">
              <div className="cf-corner" />
              <div className="cf-head">Truth: Threat</div>
              <div className="cf-head">Truth: Safe</div>
              <div className="cf-axis left">Source: Threat</div>
              <div className="cf-cell tp">
                <span className="cf-tag">TRUE POSITIVE</span>
                <span className="cf-num">{q.confirmed_tp}</span>
                <span className="cf-desc">Source correctly flagged</span>
              </div>
              <div className="cf-cell fp">
                <span className="cf-tag">FALSE POSITIVE</span>
                <span className="cf-num">{q.confirmed_fp}</span>
                <span className="cf-desc">
                  Source over-flagged (safe output)
                </span>
              </div>
              <div className="cf-axis left">Source: Safe</div>
              <div className="cf-cell fn">
                <span className="cf-tag">FALSE NEGATIVE</span>
                <span className="cf-num">{q.confirmed_fn}</span>
                <span className="cf-desc">Source missed a real threat</span>
              </div>
              <div className="cf-cell tn">
                <span className="cf-tag">TRUE NEGATIVE</span>
                <span className="cf-num">{q.confirmed_tn}</span>
                <span className="cf-desc">Source correctly cleared</span>
              </div>
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
                <Icon name="target" size={15} /> Source evaluator scores
              </h3>
              <p className="sub">
                How well the original evaluator matched confirmed truth.
              </p>
              <div className="metric-cards">
                {metrics.map((m) => (
                  <div className="metric-card" key={m.l}>
                    <div className="mc-l">{m.l}</div>
                    <div className="mc-v">{pct(m.v)}</div>
                    <div className="mc-bar">
                      <span style={{ width: `${(m.v ?? 0) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="card panel-block">
              <h3>
                <Icon name="eye" size={15} /> Review coverage
              </h3>
              <div className="coverage-ring" style={{ marginTop: 12 }}>
                <Ring value={q.review_coverage} size={92} thickness={10} />
                <div className="cr-txt">
                  <strong>{q.reviewed_cases}</strong>
                  <p>of {q.total_attempts} attempts adjudicated</p>
                  <p style={{ marginTop: 6 }}>
                    {q.alarm_threat_cases} alarm threat · {q.metric_cases}{" "}
                    scored
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
