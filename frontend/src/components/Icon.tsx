const ICONS: Record<string, string> = {
  gauge:
    "M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z M13.4 12.6 19 7 M3.5 17.5a9 9 0 1 1 17 0",
  scale:
    "M12 3v18 M7 7h10 M7 7 4 13a3 3 0 0 0 6 0L7 7Z M17 7l-3 6a3 3 0 0 0 6 0l-3-6Z M6 21h12",
  target:
    "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0-10 0 M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0",
  database:
    "M12 5c4.97 0 9-1.34 9-3s-4.03-3-9-3-9 1.34-9 3 4.03 3 9 3Z M3 2v0 M21 5v14c0 1.66-4.03 3-9 3s-9-1.34-9-3V5 M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3",
  sliders:
    "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
  sun: "M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0 M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z",
  refresh: "M21 12a9 9 0 1 1-3-6.7L21 8 M21 3v5h-5",
  search: "M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0 M21 21l-4.3-4.3",
  check: "M20 6 9 17l-5-5",
  checkCircle: "M22 11.1V12a10 10 0 1 1-5.9-9.1 M22 4 12 14.5l-3-3",
  x: "M18 6 6 18 M6 6l12 12",
  arrowRight: "M5 12h14 M13 6l6 6-6 6",
  arrowLeftRight: "M8 4 4 8l4 4 M4 8h16 M16 20l4-4-4-4 M20 16H4",
  alert:
    "M12 9v4 M12 17h.01 M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
  help: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3 M12 17h.01",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z",
  shieldHalf: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z M12 2v20",
  shieldCheck: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z M9 12l2 2 4-4",
  bolt: "M13 2 4.5 13H11l-1 9 8.5-11H12l1-9Z",
  download: "M12 3v12 M7 11l5 5 5-5 M5 21h14",
  filter: "M3 4h18l-7 8v6l-4 2v-8L3 4Z",
  chevronLeft: "M15 18l-6-6 6-6",
  chevronRight: "M9 18l6-6-6-6",
  chevronsLeft: "M11 17l-5-5 5-5 M18 17l-5-5 5-5",
  play: "M6 3l14 9-14 9V3Z",
  inbox:
    "M22 12h-6l-2 3h-4l-2-3H2 M5.5 5.5 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.5a2 2 0 0 0-1.8-1H7.3a2 2 0 0 0-1.8 1Z",
  key: "M15.5 7.5a4.5 4.5 0 1 0-4.6 4.5L4 19v2h2l1-1h2v-2h2v-2l1.9-1.9a4.5 4.5 0 0 0 2.6.4 M16.5 7.5h.01",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0",
  eyeOff:
    "M9.9 4.2A10 10 0 0 1 12 4c6.5 0 10 7 10 7a14 14 0 0 1-2.3 3 M6.6 6.6A14 14 0 0 0 2 11s3.5 7 10 7a10 10 0 0 0 4-.8 M3 3l18 18 M9.9 9.9a3 3 0 0 0 4.2 4.2",
  clock: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 7v5l3 2",
  layers: "M12 2 2 7l10 5 10-5-10-5Z M2 17l10 5 10-5 M2 12l10 5 10-5",
  lock: "M5 11h14v10H5z M8 11V7a4 4 0 0 1 8 0v4",
  fileUp:
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z M14 2v6h6 M12 18v-6 M9 15l3-3 3 3",
};

export function Icon({
  name,
  size = 16,
  className,
  style,
}: {
  name: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  const d = ICONS[name];
  if (!d) return null;
  const paths = d.split(" M").map((seg, i) => (i === 0 ? seg : "M" + seg));
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {paths.map((p, i) => (
        <path key={i} d={p} />
      ))}
    </svg>
  );
}
