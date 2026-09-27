export function QuoteMark({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`block font-serif text-6xl leading-none text-primary/25 ${className}`}
    >
      &ldquo;
    </span>
  );
}
