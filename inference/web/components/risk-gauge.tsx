import { cn } from "@/lib/utils";
import { band, type BandKey } from "@/lib/model";
import { AlertTriangle, Eye, ShieldCheck, type LucideIcon } from "lucide-react";

export const TONE: Record<BandKey, { text: string; bg: string; soft: string; border: string; stroke: string; icon: LucideIcon }> = {
  high: { text: "text-risk-high", bg: "bg-risk-high", soft: "bg-risk-high/10", border: "border-risk-high/30", stroke: "stroke-risk-high", icon: AlertTriangle },
  watch: { text: "text-risk-watch", bg: "bg-risk-watch", soft: "bg-risk-watch/12", border: "border-risk-watch/35", stroke: "stroke-risk-watch", icon: Eye },
  low: { text: "text-risk-low", bg: "bg-risk-low", soft: "bg-risk-low/10", border: "border-risk-low/30", stroke: "stroke-risk-low", icon: ShieldCheck },
};

/** Semicircle gauge: 0% on the left, 100% on the right, with tick marks at the 20% / 50% band edges. */
export function RiskGauge({ value }: { value: number }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  const tone = TONE[band(value).key];
  const arc = "M 20 110 A 90 90 0 0 1 200 110";
  const tick = (p: number) => {
    const a = Math.PI * (1 - p);
    const [cx, cy, r1, r2] = [110, 110, 74, 104];
    return { x1: cx + r1 * Math.cos(a), y1: cy - r1 * Math.sin(a), x2: cx + r2 * Math.cos(a), y2: cy - r2 * Math.sin(a) };
  };
  return (
    <div className="relative mx-auto w-full max-w-[280px]">
      <svg viewBox="0 0 220 124" className="w-full" role="img" aria-label={`Risk ${pct}%`}>
        <path d={arc} fill="none" className="stroke-muted" strokeWidth={18} strokeLinecap="round" />
        <path
          d={arc}
          fill="none"
          pathLength={100}
          strokeDasharray={100}
          strokeDashoffset={100 - pct}
          strokeWidth={18}
          strokeLinecap="round"
          className={cn("gauge-arc", tone.stroke)}
        />
        {[0.2, 0.5].map((p) => (
          <line key={p} {...tick(p)} className="stroke-border" strokeWidth={2} />
        ))}
      </svg>
      <div className="absolute inset-x-0 bottom-1 flex flex-col items-center">
        <span className={cn("text-5xl font-bold tabular-nums tracking-tight", tone.text)}>{pct}%</span>
        <span className="text-xs font-medium text-muted-foreground">chance of late or short</span>
      </div>
    </div>
  );
}

/** Horizontal Low / Watch / High scale with a marker at the score. */
export function BandScale({ value }: { value: number }) {
  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const segs: { key: BandKey; label: string; w: string }[] = [
    { key: "low", label: "Low  <20%", w: "20%" },
    { key: "watch", label: "Watch  20–50%", w: "30%" },
    { key: "high", label: "High  50%+", w: "50%" },
  ];
  return (
    <div className="space-y-1.5">
      <div className="relative">
        <div className="flex h-2.5 overflow-hidden rounded-full">
          {segs.map((s) => (
            <div key={s.key} className={cn(TONE[s.key].bg, "opacity-80")} style={{ width: s.w }} />
          ))}
        </div>
        <div
          className="absolute -top-1.5 size-0 -translate-x-1/2 border-x-[7px] border-t-[9px] border-x-transparent border-t-foreground transition-[left] duration-700"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex text-[11px] font-medium text-muted-foreground">
        {segs.map((s) => (
          <span key={s.key} style={{ width: s.w }} className="whitespace-pre">
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}
