import { Icon } from "./Icon";

const STATUS_META: Record<
  string,
  { label: string; cls: string; implies: string; icon: string }
> = {
  SOURCE_STRICTER_THAN_JUDGE: {
    label: "Source stricter",
    cls: "source-stricter",
    implies: "Suspected source false positive",
    icon: "shieldHalf",
  },
  JUDGE_STRICTER_THAN_SOURCE: {
    label: "Judge stricter",
    cls: "judge-stricter",
    implies: "Suspected source false negative",
    icon: "alert",
  },
  REVIEW_REQUIRED: {
    label: "Review required",
    cls: "review-required",
    implies: "Judge uncertain",
    icon: "help",
  },
  AGREEMENT_THREAT: {
    label: "Agreement · threat",
    cls: "agreement-threat",
    implies: "Both flagged threat",
    icon: "check",
  },
  AGREEMENT_SAFE: {
    label: "Agreement · safe",
    cls: "agreement-safe",
    implies: "Both judged safe",
    icon: "check",
  },
  EVALUATION_ERROR: {
    label: "Evaluation error",
    cls: "evaluation-error",
    implies: "Technical failure — not a verdict",
    icon: "bolt",
  },
};

export { STATUS_META };

export function StatusPill({ status }: { status: string | null }) {
  if (!status) return null;
  const meta = STATUS_META[status];
  if (!meta) return null;
  return (
    <span className={`cmp ${meta.cls}`}>
      <span className="ic">
        <Icon name={meta.icon} size={13} />
      </span>
      {meta.label}
    </span>
  );
}
