import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "cn";

/** Terminal-like window: #2A2B2E frame, optional title strip with a decorative close button. */
export function Window({ title, className, children }: { title?: string; className?: string; children: ReactNode }) {
  return (
    <section className={cn("border border-border bg-background", className)} aria-label={title}>
      {title && (
        <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-2 text-xs font-bold tracking-widest text-muted-foreground uppercase">
          <span>{title}</span>
          <CloseButton />
        </div>
      )}
      <div className="px-6 py-8 md:px-8">{children}</div>
    </section>
  );
}

/** Mocked window close button: purely decorative, never interactive. */
export function CloseButton() {
  return <span aria-hidden="true" className="inline-flex size-5 items-center justify-center bg-muted text-xs leading-none text-foreground">x</span>;
}

/** Dashed "underscore" bar used as a section separator. */
export function DashBar({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("dash-bar", className)} />;
}

const FALLBACK_COLUMNS = 40;

/**
 * `LABEL......VALUE` row. The dot leader is measured, not hard-coded: the row width, the rendered
 * label/value widths and the width of a single dot glyph are read from the DOM, so every row in a
 * column ends on the same edge regardless of label or value length.
 */
export function DotRow({ label, value, critical = false }: { label: string; value: string; critical?: boolean }) {
  const rowRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const valueRef = useRef<HTMLSpanElement>(null);
  const probeRef = useRef<HTMLSpanElement>(null);
  const [dots, setDots] = useState(() => fallbackDots(label, value));

  useLayoutEffect(() => {
    const row = rowRef.current;
    if (!row) return;
    const measure = () => {
      const width = row.clientWidth;
      const dot = probeRef.current?.getBoundingClientRect().width ?? 0;
      if (!width || !dot) { setDots(fallbackDots(label, value)); return; }
      const used = (labelRef.current?.offsetWidth ?? 0) + (valueRef.current?.offsetWidth ?? 0);
      setDots(Math.max(1, Math.floor((width - used) / dot)));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(row);
    return () => observer.disconnect();
  }, [label, value]);

  return (
    <div ref={rowRef} className="relative flex items-baseline overflow-hidden text-lg leading-none whitespace-nowrap">
      <span ref={labelRef} className="pr-2 font-bold tracking-wider uppercase">{label}</span>
      <span aria-hidden="true" className="text-muted-foreground/60">{".".repeat(dots)}</span>
      <span ref={probeRef} aria-hidden="true" className="invisible absolute">.</span>
      <span ref={valueRef} className={cn("ml-auto pl-2 font-bold", critical && "text-destructive")}>{value}</span>
    </div>
  );
}

function fallbackDots(label: string, value: string) {
  return Math.max(1, FALLBACK_COLUMNS - label.length - value.length);
}
