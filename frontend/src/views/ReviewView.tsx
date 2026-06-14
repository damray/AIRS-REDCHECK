import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  RESULTS_PAGE_SIZE,
  defaultDisagreementFilters,
  fetchAttemptDetail,
  fetchResults,
  fetchTimeline,
  filteredExportUrl,
  submitReview,
  type ResultAttempt,
  type ResultFilters,
  type ReviewDecision,
} from "../api";
import { Icon } from "../components/Icon";
import { SevTag } from "../components/SevTag";
import { StatusPill, STATUS_META } from "../components/StatusPill";
import { VerdictChip } from "../components/VerdictChip";

const BEHAVIOR_LABEL: Record<string, string> = {
  SAFE_REFUSAL: "Safe refusal",
  SAFE_REDIRECT: "Safe redirect",
  SAFE_COMPLETION: "Safe completion",
  UNSAFE_COMPLETION: "Unsafe completion",
  AMBIGUOUS: "Ambiguous",
};

const REVIEW_FILTERS = [
  { key: "__NEEDS_REVIEW__", short: "Review required" },
  { key: "SOURCE_STRICTER_THAN_JUDGE", short: "Source stricter" },
  { key: "JUDGE_STRICTER_THAN_SOURCE", short: "Judge stricter" },
  { key: "REVIEW_REQUIRED", short: "Uncertain" },
  { key: "AGREEMENT_THREAT", short: "Agree · threat" },
  { key: "AGREEMENT_SAFE", short: "Agree · safe" },
  { key: "EVALUATION_ERROR", short: "Errors" },
];

export function ReviewView({
  initialFilter,
  reviewer,
  setReviewer,
  projectId,
}: {
  initialFilter: string[];
  reviewer: string;
  setReviewer: (v: string) => void;
  projectId?: string;
}) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string[]>(initialFilter);
  const [reviewRequiredOnly, setReviewRequiredOnly] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setFilter(initialFilter);
    setOffset(0);
  }, [initialFilter]);

  const resultFilters: ResultFilters = useMemo(
    () => ({
      ...defaultDisagreementFilters(),
      comparisonStatus: filter,
      reviewed: reviewRequiredOnly ? "false" : "",
      contextContains: search,
    }),
    [filter, reviewRequiredOnly, search],
  );

  const reviewRequiredCountFilters: ResultFilters = useMemo(
    () => ({
      ...defaultDisagreementFilters(),
      comparisonStatus: filter,
      reviewed: "false",
      contextContains: search,
    }),
    [filter, search],
  );

  const resultsQuery = useQuery({
    queryKey: ["results", resultFilters, offset, projectId ?? ""],
    queryFn: () =>
      fetchResults(resultFilters, offset, RESULTS_PAGE_SIZE, projectId),
  });
  const reviewRequiredCountQuery = useQuery({
    queryKey: [
      "results",
      "review-required-count",
      reviewRequiredCountFilters,
      projectId ?? "",
    ],
    queryFn: () => fetchResults(reviewRequiredCountFilters, 0, 1, projectId),
  });

  const attempts = resultsQuery.data?.items ?? [];
  const total = resultsQuery.data?.total ?? 0;
  const reviewRequiredCount = reviewRequiredCountQuery.data?.total ?? 0;

  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    attempts.forEach((a) => {
      const s = a.comparison_status ?? "";
      m[s] = (m[s] || 0) + 1;
    });
    return m;
  }, [attempts]);

  const selected = attempts.find((a) => a.attempt_id === selectedId) ?? null;

  const attemptDetailQuery = useQuery({
    queryKey: ["attempt-detail", selectedId, projectId ?? ""],
    queryFn: () => fetchAttemptDetail(selectedId!, projectId),
    enabled: selectedId !== null,
  });

  const timelineQuery = useQuery({
    queryKey: ["timeline", selected?.stream_id, projectId ?? ""],
    queryFn: () => fetchTimeline(selected!.stream_id, projectId),
    enabled:
      selected?.input_type === "agent" &&
      (selected?.stream_id?.length ?? 0) > 0,
  });

  const reviewMutation = useMutation({
    mutationFn: submitReview,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["results"] });
      void queryClient.invalidateQueries({ queryKey: ["reviewed-quality"] });
      void queryClient.invalidateQueries({ queryKey: ["triage-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["attempt-detail"] });
    },
  });

  function toggleFilter(key: string) {
    if (key === "__NEEDS_REVIEW__") {
      setReviewRequiredOnly((value) => !value);
      setOffset(0);
      return;
    }
    setFilter((f) =>
      f.includes(key) ? f.filter((x) => x !== key) : [...f, key],
    );
    setOffset(0);
  }

  const detail = attemptDetailQuery.data ?? selected;
  const siblings =
    detail?.input_type === "agent"
      ? (timelineQuery.data?.attempts ?? []).sort(
          (a, b) => a.attempt_index - b.attempt_index,
        )
      : [];

  return (
    <div className="review-layout" aria-label="Disagreement results">
      {/* Queue */}
      <div className="queue">
        <div className="queue-head">
          <div className="queue-title">
            <h3>Review queue</h3>
            <span className="qcount">
              {total} result{total === 1 ? "" : "s"}
            </span>
          </div>
          <div className="searchbox">
            <Icon name="search" size={15} />
            <input
              aria-label="Context contains"
              placeholder="Search prompt, output, category…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setOffset(0);
              }}
            />
          </div>
          <div className="filter-chips">
            {REVIEW_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                className={`fchip${(f.key === "__NEEDS_REVIEW__" ? reviewRequiredOnly : filter.includes(f.key)) ? " active" : ""}`}
                onClick={() => toggleFilter(f.key)}
                aria-pressed={
                  f.key === "__NEEDS_REVIEW__"
                    ? reviewRequiredOnly
                    : filter.includes(f.key)
                }
              >
                {f.short}
                <span className="fc-n">
                  {f.key === "__NEEDS_REVIEW__"
                    ? reviewRequiredCount
                    : counts[f.key] || 0}
                </span>
              </button>
            ))}
            {filter.length || reviewRequiredOnly ? (
              <button
                type="button"
                className="fchip"
                onClick={() => {
                  setFilter([]);
                  setReviewRequiredOnly(false);
                  setOffset(0);
                }}
              >
                <Icon name="x" size={12} /> Clear
              </button>
            ) : null}
          </div>
        </div>
        <div className="queue-list">
          {attempts.length === 0 ? (
            <div className="queue-empty">No attempts match this filter.</div>
          ) : (
            attempts.map((a) => (
              <div
                key={a.attempt_id}
                className={`qrow${a.attempt_id === selectedId ? " active" : ""}${a.review_decision ? " reviewed" : ""}`}
                onClick={() => setSelectedId(a.attempt_id)}
              >
                <div className="qrow-top">
                  <span className="qrow-id mono">
                    {a.external_stream_id ?? a.stream_id.slice(0, 12)}
                    {a.input_type === "agent" ? ` · t${a.attempt_index}` : ""}
                  </span>
                  <div className="qrow-verdicts">
                    <VerdictChip verdict={a.source_verdict} />
                    <span className="qrow-arrow">
                      <Icon name="arrowRight" size={12} />
                    </span>
                    {a.comparison_status === "EVALUATION_ERROR" ? (
                      <span className="chip error">
                        <span className="dot" />
                        ERR
                      </span>
                    ) : (
                      <VerdictChip verdict={a.judge_verdict} />
                    )}
                  </div>
                </div>
                <div className="qrow-snippet">{a.source_output}</div>
                <div className="qrow-meta">
                  <StatusPill status={a.comparison_status} />
                  <span className="review-check qrow-rev">
                    <input
                      aria-label={`Review decision made for ${a.attempt_id}`}
                      checked={Boolean(a.review_decision)}
                      readOnly
                      tabIndex={-1}
                      type="checkbox"
                    />
                    Reviewed
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
        <div
          style={{
            padding: "10px 16px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <button
            className="btn sm"
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - RESULTS_PAGE_SIZE))}
          >
            Previous
          </button>
          <span className="muted" style={{ fontSize: 12 }}>
            {total === 0
              ? "0 results"
              : `${offset + 1}–${Math.min(offset + RESULTS_PAGE_SIZE, total)} of ${total}`}
          </span>
          <button
            className="btn sm"
            type="button"
            disabled={offset + RESULTS_PAGE_SIZE >= total}
            onClick={() => setOffset(offset + RESULTS_PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      </div>

      {/* Detail */}
      <div className="detail" aria-label="Attempt detail panel">
        {!detail ? (
          <div className="detail-empty">
            <div>
              <div className="de-ic">
                <Icon name="scale" size={26} />
              </div>
              <strong style={{ fontSize: 15, color: "var(--ink-2)" }}>
                Select an attempt to adjudicate
              </strong>
              <p style={{ marginTop: 6, fontSize: 13 }}>
                Compare the source verdict against the blind Judge,
                <br />
                then confirm the correct call.
              </p>
            </div>
          </div>
        ) : (
          <AttemptDetail
            attempt={detail}
            siblings={siblings}
            onSelectSibling={setSelectedId}
            onReview={(decision, comment) => {
              reviewMutation.mutate({
                attemptId: detail.attempt_id,
                decision,
                reviewerIdentity: reviewer.trim() || "analyst",
                comment: comment?.trim() || null,
              });
            }}
            reviewer={reviewer}
            setReviewer={setReviewer}
            reviewPending={reviewMutation.isPending}
            reviewSuccess={reviewMutation.isSuccess}
            reviewError={reviewMutation.error}
            exportUrl={filteredExportUrl(resultFilters, projectId)}
          />
        )}
      </div>
    </div>
  );
}

function AttemptDetail({
  attempt: a,
  siblings,
  onSelectSibling,
  onReview,
  reviewer,
  setReviewer,
  reviewPending,
  reviewSuccess,
  reviewError,
  exportUrl,
}: {
  attempt: ResultAttempt;
  siblings: ResultAttempt[];
  onSelectSibling: (id: string) => void;
  onReview: (decision: ReviewDecision, comment: string | null) => void;
  reviewer: string;
  setReviewer: (v: string) => void;
  reviewPending: boolean;
  reviewSuccess: boolean;
  reviewError: unknown;
  exportUrl: string;
}) {
  const [comment, setComment] = useState("");
  const meta = STATUS_META[a.comparison_status ?? ""];
  const isError = a.comparison_status === "EVALUATION_ERROR";
  const isDisagreement = [
    "SOURCE_STRICTER_THAN_JUDGE",
    "JUDGE_STRICTER_THAN_SOURCE",
    "REVIEW_REQUIRED",
  ].includes(a.comparison_status ?? "");

  useEffect(() => {
    setComment("");
  }, [a.attempt_id]);

  const impliesText: Record<string, React.ReactNode> = {
    SOURCE_STRICTER_THAN_JUDGE: (
      <span>
        Source flagged <em>THREAT</em> but the Judge read the output as{" "}
        <em>SAFE</em> — a <strong>suspected source false positive</strong>.
        Confirm whether the output is actually harmful.
      </span>
    ),
    JUDGE_STRICTER_THAN_SOURCE: (
      <span>
        Source cleared this as <em>SAFE</em> but the Judge flagged{" "}
        <em>THREAT</em> — a <strong>suspected source false negative</strong>. A
        missed threat is the costlier error.
      </span>
    ),
    REVIEW_REQUIRED: (
      <span>
        The Judge was <em>uncertain</em> about this output. Human judgment
        decides the verdict.
      </span>
    ),
    AGREEMENT_THREAT: (
      <span>
        Source and Judge both flagged <em>THREAT</em>. Confirm to record a true
        positive.
      </span>
    ),
    AGREEMENT_SAFE: (
      <span>
        Source and Judge both judged this <em>SAFE</em>. Confirm to record a
        true negative.
      </span>
    ),
    EVALUATION_ERROR: (
      <span>
        A technical failure prevented evaluation. This is{" "}
        <strong>not a safety verdict</strong> — re-run the attempt once the
        gateway recovers.
      </span>
    ),
  };

  const bannerIcon = isError
    ? "bolt"
    : a.comparison_status === "REVIEW_REQUIRED"
      ? "help"
      : a.comparison_status?.startsWith("AGREEMENT")
        ? "check"
        : "alert";

  return (
    <div className="detail-inner">
      {/* header */}
      <div className="detail-head">
        <div className="detail-eyebrow">
          <span
            className="mono"
            style={{ fontSize: 12, color: "var(--ink-3)" }}
          >
            {a.external_stream_id ?? a.stream_id.slice(0, 12)}
          </span>
          <span className="tag">
            {a.input_type === "agent" ? "Agent" : "Static"}
          </span>
          {a.input_type === "agent" ? (
            <span
              className="mono"
              style={{ fontSize: 11.5, color: "var(--ink-faint)" }}
            >
              attempt {a.attempt_index + 1} of {siblings.length || "?"}
            </span>
          ) : null}
          <div style={{ marginLeft: "auto" }}>
            <StatusPill status={a.comparison_status} />
          </div>
        </div>
        <div className="detail-tags">
          <SevTag sev={a.severity as string | null} />
          {a.category ? (
            <span className="tag">{String(a.category)}</span>
          ) : null}
          {a.technique ? (
            <span className="tag">
              <Icon name="bolt" size={12} /> {String(a.technique)}
            </span>
          ) : null}
        </div>
      </div>

      {/* implication banner */}
      {meta ? (
        <div className={`implies-banner ${meta.cls}`}>
          <span className="ib-ic" style={{ background: "currentColor" }}>
            <span
              style={{
                color: "var(--surface)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <Icon name={bannerIcon} size={16} />
            </span>
          </span>
          <span className="ib-txt">
            {impliesText[a.comparison_status ?? ""]}
          </span>
        </div>
      ) : null}

      {/* prompt + output */}
      <div className="io-block">
        <div className="io-label">
          <Icon name="arrowRight" size={13} /> Source prompt{" "}
          <span className="io-note">
            · what the attacker sent (not evaluated)
          </span>
        </div>
        <div className="io-body">{a.source_prompt}</div>
      </div>
      <div className="io-block output">
        <div className="io-label">
          <Icon name="shield" size={13} /> Model output{" "}
          <span className="io-note">· the response being judged</span>
        </div>
        <div className="io-body">{a.source_output}</div>
      </div>

      {/* error detail */}
      {isError ? (
        <div className="err-detail">
          <div className="ed-row">
            <span className="ed-k">Error code</span>
            <span className="ed-v">{a.evaluation_error_code ?? "Unknown"}</span>
          </div>
          <div className="ed-row">
            <span className="ed-k">Message</span>
            <span className="ed-v" style={{ fontFamily: "var(--font-ui)" }}>
              {a.evaluation_error_message ?? "Unknown"}
            </span>
          </div>
          <div className="ed-row">
            <span className="ed-k">Timestamp</span>
            <span className="ed-v">
              {a.evaluation_error_created_at ?? "Unknown"}
            </span>
          </div>
        </div>
      ) : null}

      {/* compare */}
      {!isError ? (
        <div className="compare">
          <div className="cmp-col source">
            <div className="cmp-colhead">
              <span className="cch-l">
                <span
                  className="cch-ic"
                  style={{
                    background: "var(--surface-3)",
                    color: "var(--ink-3)",
                  }}
                >
                  <Icon name="database" size={13} />
                </span>{" "}
                Source evaluator
              </span>
            </div>
            <div className="cmp-verdict-big">
              <VerdictChip verdict={a.source_verdict} size="lg" />
            </div>
            <div className="cmp-field">
              <div className="cf-l">Category</div>
              <div className="cf-v">
                {a.category ? String(a.category) : "—"}
              </div>
            </div>
            <div className="cmp-field">
              <div className="cf-l">Reasoning</div>
              <div
                className="cf-v"
                style={{ color: "var(--ink-3)", fontStyle: "italic" }}
              >
                Not provided to Judge — withheld to preserve blind evaluation.
              </div>
            </div>
          </div>

          <div className="cmp-mid">
            <div className="delta-badge">
              <Icon
                name="arrowLeftRight"
                size={16}
                style={{ color: "var(--ink-3)" }}
              />
            </div>
            <div className="delta-label">
              {isDisagreement ? "Disagree" : "Agree"}
            </div>
          </div>

          <div className="cmp-col judge">
            <div className="cmp-colhead">
              <span className="cch-l">
                <span
                  className="cch-ic"
                  style={{
                    background: "var(--accent-soft)",
                    color: "var(--accent)",
                  }}
                >
                  <Icon name="shieldCheck" size={13} />
                </span>{" "}
                Blind Judge
              </span>
            </div>
            <div className="cmp-verdict-big">
              <VerdictChip verdict={a.judge_verdict} size="lg" />
            </div>
            <div className="cmp-field">
              <div className="cf-l">Risk category</div>
              <div className="cf-v">—</div>
            </div>
            <div className="cmp-field">
              <div className="cf-l">Explanation</div>
              <div className="cf-v cmp-explain">—</div>
            </div>
          </div>
        </div>
      ) : null}

      {/* agent timeline */}
      {a.input_type === "agent" && siblings.length > 1 ? (
        <div className="timeline" aria-label="Agent timeline">
          <h3>
            <Icon name="clock" size={14} /> Stream timeline · {siblings.length}{" "}
            attempts
          </h3>
          <div className="tl-track">
            {siblings.map((s) => (
              <div
                key={s.attempt_id}
                className={`tl-item${s.attempt_id === a.attempt_id ? " active" : ""}${s.judge_verdict === "THREAT" ? " threat" : s.judge_verdict === "SAFE" ? " safe" : ""}`}
                onClick={() => onSelectSibling(s.attempt_id)}
              >
                <div className="tl-top">
                  <span className="tl-idx">Attempt {s.attempt_index + 1}</span>
                  <VerdictChip verdict={s.source_verdict} />
                  <Icon
                    name="arrowRight"
                    size={11}
                    style={{ color: "var(--ink-faint)" }}
                  />
                  {s.comparison_status === "EVALUATION_ERROR" ? (
                    <span className="chip error">
                      <span className="dot" />
                      ERR
                    </span>
                  ) : (
                    <VerdictChip verdict={s.judge_verdict} />
                  )}
                  {s.attempt_id === a.attempt_id ? (
                    <span className="tag" style={{ marginLeft: "auto" }}>
                      viewing
                    </span>
                  ) : null}
                </div>
                <div className="tl-prompt">{s.source_prompt}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* adjudication */}
      {!isError ? (
        <div className="adjudicate" aria-label="Adjudication form">
          <h3>
            <Icon name="scale" size={15} /> Adjudication
          </h3>
          <p className="adj-sub">
            {isDisagreement
              ? "Resolve the disagreement — your decision becomes ground truth."
              : "Confirm the agreed verdict to record it for quality metrics."}
          </p>

          {a.review_decision ? (
            <div className="adj-done">
              <input
                aria-label="Review decision made"
                checked
                className="review-check-input"
                readOnly
                type="checkbox"
              />
              <div className="ad-body">
                <strong>
                  Adjudicated ·{" "}
                  {a.review_decision === "CONFIRM_SOURCE"
                    ? "Confirmed source verdict"
                    : a.review_decision === "CONFIRM_JUDGE"
                      ? "Confirmed Judge verdict"
                      : "Marked ambiguous"}
                </strong>
                <p>
                  by {a.reviewer_identity || "analyst"}
                  {a.reviewed_at
                    ? ` · ${new Date(a.reviewed_at).toLocaleString()}`
                    : ""}
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="adj-choices">
                <button
                  className="adj-choice"
                  type="button"
                  onClick={() => onReview("CONFIRM_SOURCE", comment)}
                  disabled={reviewPending || !reviewer.trim()}
                >
                  <div className="ac-top">
                    <Icon name="database" size={15} /> Confirm source
                  </div>
                  <div className="ac-desc">
                    Source verdict (<b>{a.source_verdict}</b>) is correct.
                  </div>
                </button>
                <button
                  className="adj-choice"
                  type="button"
                  onClick={() => onReview("CONFIRM_JUDGE", comment)}
                  disabled={reviewPending || !reviewer.trim()}
                >
                  <div className="ac-top">
                    <Icon name="shieldCheck" size={15} /> Confirm Judge
                  </div>
                  <div className="ac-desc">
                    Judge verdict (<b>{a.judge_verdict || "—"}</b>) is correct.
                  </div>
                </button>
                <button
                  className="adj-choice"
                  type="button"
                  onClick={() => onReview("AMBIGUOUS", comment)}
                  disabled={reviewPending || !reviewer.trim()}
                >
                  <div className="ac-top">
                    <Icon name="help" size={15} /> Ambiguous
                  </div>
                  <div className="ac-desc">
                    Genuinely unclear — exclude from metrics.
                  </div>
                </button>
              </div>
              <div className="adj-meta">
                <div className="adj-field">
                  <label>Reviewer</label>
                  <input
                    aria-label="Reviewer"
                    value={reviewer}
                    onChange={(e) => setReviewer(e.target.value)}
                    style={{ width: 140 }}
                  />
                </div>
                <div className="adj-field grow">
                  <label>
                    Comment{" "}
                    <span
                      style={{
                        fontWeight: 400,
                        color: "var(--ink-faint)",
                      }}
                    >
                      · optional
                    </span>
                  </label>
                  <input
                    aria-label="Comment"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Rationale for the audit trail…"
                  />
                </div>
              </div>
            </>
          )}
          {reviewSuccess ? (
            <p
              style={{
                color: "var(--safe)",
                fontSize: 13,
                fontWeight: 600,
                marginTop: 10,
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Icon name="checkCircle" size={16} /> Review saved
            </p>
          ) : null}
          {reviewError ? (
            <p style={{ color: "var(--threat)", fontSize: 13, marginTop: 10 }}>
              {reviewError instanceof Error
                ? reviewError.message
                : "Review failed"}
            </p>
          ) : null}
        </div>
      ) : null}

      {/* export link */}
      <div style={{ marginTop: 16 }}>
        <a
          className="btn sm"
          href={exportUrl}
          download
          style={{ textDecoration: "none" }}
        >
          <Icon name="download" size={13} /> Export current view
        </a>
      </div>
    </div>
  );
}
