export function SevTag({ sev }: { sev: string | null | undefined }) {
  if (!sev) return null;
  const s = String(sev);
  const cls =
    s === "Critical" || s === "High" || s === "CRITICAL" || s === "HIGH"
      ? "sev-high"
      : s === "Medium" || s === "MEDIUM"
        ? "sev-medium"
        : "sev-low";
  return <span className={`tag ${cls}`}>{s}</span>;
}
