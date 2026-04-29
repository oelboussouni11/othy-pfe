import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/audits";

const STYLES: Record<Severity, string> = {
  critical: "bg-destructive/15 text-destructive",
  warning: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  info: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
  ok: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
};

const LABELS: Record<Severity, string> = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
  ok: "OK",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        STYLES[severity],
      )}
    >
      {LABELS[severity]}
    </span>
  );
}
