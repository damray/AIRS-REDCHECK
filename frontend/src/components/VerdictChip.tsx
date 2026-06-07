export function VerdictChip({
  verdict,
  size,
}: {
  verdict: string | null;
  size?: "lg";
}) {
  if (!verdict) {
    return (
      <span className="chip neutral">
        <span className="dot" />—
      </span>
    );
  }
  const cls =
    verdict === "THREAT" ? "threat" : verdict === "SAFE" ? "safe" : "uncertain";
  return (
    <span
      className={`chip ${cls}`}
      style={
        size === "lg" ? { fontSize: "12.5px", padding: "3px 10px" } : undefined
      }
    >
      <span className="dot" />
      {verdict}
    </span>
  );
}
