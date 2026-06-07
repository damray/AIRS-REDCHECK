export function Donut({
  segments,
  size = 120,
  thickness = 18,
  centerLabel,
  centerSub,
}: {
  segments: Array<{ label: string; value: number; color: string }>;
  size?: number;
  thickness?: number;
  centerLabel?: string | number;
  centerSub?: string;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth={thickness}
        />
        {segments.map((s, i) => {
          const len = (s.value / total) * c;
          const el = (
            <circle
              key={i}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
            />
          );
          offset += len;
          return el;
        })}
      </g>
      {centerLabel !== undefined ? (
        <text
          x="50%"
          y="48%"
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: size * 0.22,
            fontWeight: 600,
            fill: "var(--ink)",
          }}
        >
          {centerLabel}
        </text>
      ) : null}
      {centerSub ? (
        <text
          x="50%"
          y="63%"
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: size * 0.085, fill: "var(--ink-3)" }}
        >
          {centerSub}
        </text>
      ) : null}
    </svg>
  );
}
