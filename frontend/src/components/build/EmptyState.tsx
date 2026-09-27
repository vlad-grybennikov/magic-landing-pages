import { MicIcon, SendIcon, SparklesIcon } from "./icons";

const EXAMPLES = [
  "a landing page for Maria’s Bakery, for young families, to take online orders",
  "a page for Apex Plumbing aimed at homeowners, to collect quote requests",
  "a site for GreenLeaf Yoga -- just a hero and an FAQ",
];

export function EmptyState({
  isRecording,
  isWorking,
  rejection,
  onPick,
}: {
  isRecording: boolean;
  isWorking: boolean;
  rejection: { stage: string; message: string } | null;
  onPick: (text: string) => void;
}) {
  const showRejection = rejection && !isWorking && !isRecording;

  return (
    <div className="panel relative flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-5 sm:p-8">
      <div
        className="brand-field pointer-events-none absolute inset-0"
        aria-hidden
      />

      <div className="relative my-auto flex w-full max-w-xl flex-col items-center text-center">
        {showRejection ? (
          <>
            <Tile tone="danger">
              <span className="text-xl leading-none">!</span>
            </Tile>
            <Heading>Rejected at the {rejection.stage} gate</Heading>
            <Lede>{rejection.message}</Lede>
            <p className="mt-3 text-xs text-ui-faint">
              The validator refused to render an invalid page -- nothing was
              saved.
            </p>
          </>
        ) : isWorking ? (
          <>
            <Tile>
              <SparklesIcon className="h-5 w-5 animate-pulse" />
            </Tile>
            <Heading>Building your page</Heading>
            <Lede>
              Choosing the sections, writing the copy, picking the photos and
              the palette -- each step is validated before the next one runs.
            </Lede>
          </>
        ) : isRecording ? (
          <>
            <Tile tone="recording">
              <MicIcon className="h-5 w-5" />
            </Tile>
            <Heading>Listening…</Heading>
            <Lede>
              Describe the page you want, then tap the mic again to send.
            </Lede>
          </>
        ) : (
          <>
            <Tile>
              <SparklesIcon className="h-5 w-5" />
            </Tile>
            <h2 className="mt-5 text-xl font-semibold tracking-tight text-ui-text sm:text-2xl">
              Describe it. We’ll build it.
            </h2>
            <Lede>
              Say or type what the page is for. The builder writes the copy,
              picks the photos and chooses a palette -- then validates the lot.
            </Lede>

            <ul className="mt-5 flex w-full flex-col gap-2 sm:mt-7">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button
                    type="button"
                    onClick={() => onPick(example)}
                    disabled={isWorking}
                    className="group flex w-full items-center gap-3 rounded-xl border border-ui-border bg-ui-surface/80 px-3 py-2.5 text-left backdrop-blur-sm transition-all hover:-translate-y-px hover:border-ui-accent/40 hover:shadow-[0_4px_14px_rgba(79,70,229,0.10)] disabled:opacity-50"
                  >
                    <span className="brand-gradient flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white opacity-80 transition-opacity group-hover:opacity-100">
                      <SparklesIcon className="h-3.5 w-3.5" />
                    </span>
                    <span className="min-w-0 flex-1 text-sm leading-6 text-ui-muted transition-colors group-hover:text-ui-text">
                      {example}
                    </span>
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-ui-faint opacity-0 transition-all group-hover:bg-ui-accent-soft group-hover:text-ui-accent group-hover:opacity-100">
                      <SendIcon className="h-3.5 w-3.5" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mt-5 text-lg font-semibold tracking-tight text-ui-text">
      {children}
    </h2>
  );
}

function Lede({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-2 max-w-md text-sm leading-6 text-ui-muted">{children}</p>
  );
}

function Tile({
  tone = "brand",
  children,
}: {
  tone?: "brand" | "danger" | "recording";
  children: React.ReactNode;
}) {
  const tones = {
    brand: "brand-gradient text-white shadow-[0_8px_24px_rgba(79,70,229,0.28)]",
    danger: "bg-ui-danger-soft text-ui-danger",
    recording: "bg-red-500 text-white shadow-[0_8px_24px_rgba(239,68,68,0.28)]",
  };
  return (
    <span
      className={`flex h-12 w-12 items-center justify-center rounded-2xl ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
