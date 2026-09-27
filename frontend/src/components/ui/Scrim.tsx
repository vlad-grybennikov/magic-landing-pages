export function Scrim({ strength = "md" }: { strength?: "sm" | "md" | "lg" }) {
  const strengths = {
    sm: "from-black/50 via-black/10 to-transparent",
    md: "from-black/70 via-black/30 to-black/5",
    lg: "from-black/80 via-black/55 to-black/25",
  };
  return (
    <div
      aria-hidden
      className={`absolute inset-0 bg-gradient-to-t ${strengths[strength]}`}
    />
  );
}
