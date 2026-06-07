export function Ring({
  value,
  size = 84,
  thickness = 9,
  color = "var(--accent)",
}: {
  value: number;
  size?: number;
  thickness?: number;
  color?: string;
}) {
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const len = Math.max(0, Math.min(1, value)) * c;
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
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={thickness}
          strokeDasharray={`${len} ${c - len}`}
          strokeLinecap="round"
        />
      </g>
      <text
        x="50%"
        y="52%"
        textAnchor="middle"
        dominantBaseline="middle"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: size * 0.26,
          fontWeight: 600,
          fill: "var(--ink)",
        }}
      >
        {Math.round(value * 100)}%
      </text>
    </svg>
  );
}
