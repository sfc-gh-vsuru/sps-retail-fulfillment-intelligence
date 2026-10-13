"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, BookOpen, Boxes, Building2, CheckCircle2, ChevronRight,
  CircleDollarSign, Code2, Cpu, Factory, FlaskConical, Gauge, History, Info, Laptop, ListChecks, Loader2, Lock,
  MapPin, Package, RotateCcw, Sparkles, Store, Timer, TrendingUp, Truck, Warehouse, XCircle, Zap,
} from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BandScale, RiskGauge, TONE } from "@/components/risk-gauge";
import { cn } from "@/lib/utils";
import {
  CORTEX_MODEL, EDITABLE, FEATURES, NETWORK_FAILURE_RATE, RETAILERS, band, type OrderRecord,
} from "@/lib/model";

type ScoreResult = {
  url: string;
  latencyMs: number;
  request: unknown;
  response: unknown;
  results: { row: number; riskProbability: number; riskClass: number }[];
};
type ExplainResult = { url: string; latencyMs: number; model: string; text: string };

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("en-US");
const pct = (v: number) => `${Math.round(v * 100)}%`;
const wasLate = (o: OrderRecord) => o.ACTUAL_OUTCOME !== "Delivered OTIF";

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data as T;
}

export function RiskChecker() {
  const [samples, setSamples] = useState<OrderRecord[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [order, setOrder] = useState<OrderRecord | null>(null);
  const [withAi, setWithAi] = useState(true);

  const [scoring, setScoring] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [scoredOrder, setScoredOrder] = useState<OrderRecord | null>(null);
  const [previous, setPrevious] = useState<{ poId: string; risk: number } | null>(null);

  const [explaining, setExplaining] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<ExplainResult | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/samples")
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
        if (!active) return;
        setSamples(data);
        setOrder({ ...data[0] });
      })
      .catch((e) => active && setLoadError((e as Error).message));
    return () => {
      active = false;
    };
  }, []);

  const original = samples?.[selected];
  const edited = useMemo(
    () => (order && original ? EDITABLE.filter((k) => order[k] !== original[k]) : []),
    [order, original],
  );

  function pick(i: number) {
    if (!samples) return;
    setSelected(i);
    setOrder({ ...samples[i] });
    setResult(null);
    setExplanation(null);
    setScoreError(null);
    setExplainError(null);
    setPrevious(null);
  }

  function update(key: string, value: string | number) {
    setOrder((o) => (o ? { ...o, [key]: value } : o));
  }

  async function runScore() {
    if (!order) return;
    const snapshot = { ...order };
    setScoring(true);
    setScoreError(null);
    setExplainError(null);
    setExplanation(null);
    if (result && scoredOrder) setPrevious({ poId: String(scoredOrder.PO_ID), risk: result.results[0].riskProbability });
    try {
      const r = await postJson<ScoreResult>("/api/score", { record: snapshot });
      setResult(r);
      setScoredOrder(snapshot);
      if (withAi) {
        setExplaining(true);
        postJson<ExplainResult>("/api/explain", { record: snapshot, riskProbability: r.results[0].riskProbability })
          .then(setExplanation)
          .catch((e) => setExplainError((e as Error).message))
          .finally(() => setExplaining(false));
      }
    } catch (e) {
      setResult(null);
      setScoreError((e as Error).message);
    } finally {
      setScoring(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <Header />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-8 sm:px-6">
        <Intro />

        {loadError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Couldn&apos;t load sample orders from Snowflake</AlertTitle>
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          {/* ── Left: choose + adjust ─────────────────────────────── */}
          <div className="space-y-6">
            <Card className="animate-rise">
              <CardHeader>
                <StepTitle n={1} icon={ListChecks} title="Choose an order" />
                <CardDescription>
                  Six real orders from history: three that arrived on time and in full, three that were late or short.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <SamplePicker samples={samples} selected={selected} onPick={pick} />
                {order && original ? <OrderSummary order={original} /> : <Skeleton className="h-36 w-full rounded-xl" />}
              </CardContent>
            </Card>

            <Card className="animate-rise [animation-delay:80ms]">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <FlaskConical className="size-4 text-brand" /> Adjust the order
                      <span className="text-xs font-normal text-muted-foreground">(optional)</span>
                    </CardTitle>
                    <CardDescription>Change a value to see how the risk responds.</CardDescription>
                  </div>
                  {edited.length > 0 && (
                    <Button variant="outline" size="sm" onClick={() => original && setOrder({ ...original })}>
                      <RotateCcw /> Reset
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {order ? <OrderInputs order={order} edited={edited} onChange={update} /> : <Skeleton className="h-40 w-full" />}
                {edited.length > 0 && (
                  <div className="flex items-center gap-2 rounded-lg border border-brand/25 bg-accent px-3 py-2 text-xs text-accent-foreground">
                    <FlaskConical className="size-3.5 shrink-0" />
                    What-if mode: you changed {edited.length} value{edited.length > 1 ? "s" : ""}, so &ldquo;what actually
                    happened&rdquo; no longer applies.
                  </div>
                )}
                <Separator />
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <Switch id="ai" checked={withAi} onCheckedChange={setWithAi} />
                    <Label htmlFor="ai" className="flex items-center gap-1.5 text-sm">
                      <Sparkles className="size-4 text-brand" /> Include an AI explanation
                    </Label>
                  </div>
                  <Button size="lg" className="h-11 px-6 text-sm font-semibold shadow-sm" disabled={!order || scoring} onClick={runScore}>
                    {scoring ? <Loader2 className="animate-spin" /> : <Zap />}
                    {scoring ? "Scoring…" : "Score this order"}
                    {!scoring && <ArrowRight />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* ── Right: result + explanation ───────────────────────── */}
          <div className="space-y-6">
            <ResultCard
              scoring={scoring}
              error={scoreError}
              result={result}
              order={scoredOrder}
              edited={scoredOrder && original ? EDITABLE.some((k) => scoredOrder[k] !== original[k]) : false}
              previous={previous && scoredOrder && previous.poId === scoredOrder.PO_ID ? previous.risk : null}
            />
            {(withAi || explanation) && result && (
              <ExplanationCard loading={explaining} error={explainError} explanation={explanation} />
            )}
          </div>
        </div>

        <Card className="animate-rise [animation-delay:160ms]">
          <CardContent className="pt-2">
            <Accordion>
              <AccordionItem value="read">
                <AccordionTrigger>
                  <span className="flex items-center gap-2"><Gauge className="size-4 text-brand" /> How to read the score</span>
                </AccordionTrigger>
                <AccordionContent>
                  <ul className="grid gap-2 text-muted-foreground sm:grid-cols-2">
                    <Li>The score is the model&apos;s estimate of the chance this order arrives <b>late, short, or both</b>.</Li>
                    <Li>A typical order in this network has about a <b>{pct(NETWORK_FAILURE_RATE)}</b> chance.</Li>
                    <Li><b className="text-risk-low">Low</b> is under 20%, <b className="text-risk-watch">Watch</b> is 20–50%, and <b className="text-risk-high">High</b> is 50% or more.</Li>
                    <Li>On orders it hadn&apos;t seen before, the model was right about <b>88%</b> of the time. When it flags high risk, it&apos;s right about <b>9 times out of 10</b>.</Li>
                  </ul>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="features">
                <AccordionTrigger>
                  <span className="flex items-center gap-2"><Boxes className="size-4 text-brand" /> Every detail the model uses (23)</span>
                </AccordionTrigger>
                <AccordionContent>
                  {order && (
                    <div className="grid gap-x-6 gap-y-1 font-mono text-xs sm:grid-cols-2 lg:grid-cols-3">
                      {FEATURES.map((k) => (
                        <div key={k} className="flex justify-between gap-2 border-b border-dashed py-1">
                          <span className="text-muted-foreground">{k}</span>
                          <span className={cn("font-medium", edited.includes(k) && "text-brand")}>{String(order[k])}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="tech">
                <AccordionTrigger>
                  <span className="flex items-center gap-2"><Code2 className="size-4 text-brand" /> Behind the scenes (technical)</span>
                </AccordionTrigger>
                <AccordionContent>
                  <TechDetails result={result} explanation={explanation} />
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="glossary">
                <AccordionTrigger>
                  <span className="flex items-center gap-2"><BookOpen className="size-4 text-brand" /> Glossary</span>
                </AccordionTrigger>
                <AccordionContent>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    {[
                      ["Purchase order (PO)", "A retailer's order to a supplier: what to send, how many, where, and by when."],
                      ["OTIF (on time, in full)", "The order arrived by the requested date with the full quantity."],
                      ["Late or short", "The order missed the date, was missing items, or both."],
                      ["Ship notice (ASN / EDI 856)", "The supplier's message saying what was shipped and when."],
                      ["SPS Commerce", "The network that carries order, shipment, and invoice messages between retailers and suppliers. The model combines that data with each retailer's store information."],
                    ].map(([t, d]) => (
                      <div key={t} className="rounded-lg bg-muted/60 p-3">
                        <dt className="font-semibold text-foreground">{t}</dt>
                        <dd className="text-muted-foreground">{d}</dd>
                      </div>
                    ))}
                  </dl>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      </main>
      <footer className="border-t bg-card py-4 text-center text-xs text-muted-foreground">
        Runs on your laptop, outside Snowflake. The data, the model, and the AI all stay in Snowflake.
      </footer>
    </div>
  );
}

/* ─────────────────────────── Layout pieces ─────────────────────────── */

function Header() {
  return (
    <header className="bg-brand-deep text-primary-foreground">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-brand shadow-inner">
            <Package className="size-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight tracking-tight">SPS PO Risk Checker</h1>
            <p className="text-xs opacity-70">Will this purchase order arrive on time and in full?</p>
          </div>
        </div>
        <div className="hidden items-center gap-2 text-xs sm:flex">
          <Pill icon={Cpu}>Snowflake ML</Pill>
          <Pill icon={Sparkles}>Cortex AI</Pill>
        </div>
      </div>
    </header>
  );
}

function Pill({ icon: Icon, children }: { icon: typeof Cpu; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3 py-1 font-medium">
      <Icon className="size-3.5" /> {children}
    </span>
  );
}

function Intro() {
  const steps = [
    { icon: ListChecks, title: "Pick an order", text: "Start from a real historical order, or change the numbers to try a what-if." },
    { icon: Gauge, title: "Score it", text: "A machine-learning model trained on 9,919 past orders returns a risk %." },
    { icon: Sparkles, title: "Understand it", text: "An AI assistant explains what drives the score and what to do." },
  ];
  return (
    <section className="animate-rise space-y-5">
      <p className="max-w-3xl text-[15px] leading-relaxed text-muted-foreground">
        When a retailer orders goods from a supplier, the order should arrive <b className="text-foreground">on time and in full</b> (OTIF).
        About <b className="text-foreground">1 in 5</b> orders in this network don&apos;t. This tool estimates the chance that a specific
        order will arrive <b className="text-foreground">late or short</b>, and explains why in plain English, so teams can act before the
        store is affected.
      </p>
      <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        {steps.map((s, i) => (
          <div key={s.title} className="contents">
            <div className="flex gap-3 rounded-xl border bg-card p-4 shadow-xs">
              <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-brand">
                <s.icon className="size-4.5" />
              </div>
              <div>
                <p className="text-sm font-semibold">
                  <span className="text-brand">{i + 1}.</span> {s.title}
                </p>
                <p className="text-xs leading-relaxed text-muted-foreground">{s.text}</p>
              </div>
            </div>
            {i < steps.length - 1 && <ChevronRight className="hidden size-5 self-center text-muted-foreground/60 md:block" />}
          </div>
        ))}
      </div>
    </section>
  );
}

function StepTitle({ n, icon: Icon, title }: { n: number; icon: typeof Cpu; title: string }) {
  return (
    <CardTitle className="flex items-center gap-2.5 text-base">
      <span className="grid size-6 place-items-center rounded-full bg-brand text-xs font-bold text-primary-foreground">{n}</span>
      <Icon className="size-4 text-brand" /> {title}
    </CardTitle>
  );
}

function Li({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-2">
      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand" />
      <span>{children}</span>
    </li>
  );
}

/* ─────────────────────────── Step 1 ─────────────────────────── */

function SamplePicker({ samples, selected, onPick }: { samples: OrderRecord[] | null; selected: number; onPick: (i: number) => void }) {
  if (!samples) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[62px] rounded-lg" />)}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {samples.map((s, i) => {
        const late = wasLate(s);
        const active = i === selected;
        return (
          <button
            key={String(s.PO_ID)}
            type="button"
            onClick={() => onPick(i)}
            className={cn(
              "group rounded-lg border bg-card p-2.5 text-left transition-all hover:-translate-y-0.5 hover:shadow-md",
              active ? "border-brand ring-2 ring-brand/20" : "hover:border-brand/40",
            )}
          >
            <div className="flex items-center justify-between gap-1">
              <span className="truncate text-xs font-semibold">{RETAILERS[String(s.RETAILER_ID)]}</span>
              <span className={cn("size-2 shrink-0 rounded-full", late ? "bg-risk-high" : "bg-risk-low")} />
            </div>
            <div className="font-mono text-[11px] text-muted-foreground">{String(s.PO_ID)}</div>
            <div className={cn("mt-0.5 text-[11px] font-medium", late ? "text-risk-high" : "text-risk-low")}>
              {late ? "Was late / short" : "Arrived OTIF"}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function OrderSummary({ order }: { order: OrderRecord }) {
  const late = wasLate(order);
  const LocIcon = order.LOCATION_TYPE === "STORE" ? Store : Warehouse;
  const stats = [
    { icon: Building2, label: "Retailer", value: RETAILERS[String(order.RETAILER_ID)] },
    { icon: Package, label: "Units", value: num.format(Number(order.TOTAL_UNITS)) },
    { icon: CircleDollarSign, label: "Order value", value: usd.format(Number(order.TOTAL_COST)) },
    { icon: LocIcon, label: "Destination", value: `${order.DESTINATION_SIZE} ${String(order.LOCATION_TYPE).toLowerCase()}` },
    { icon: MapPin, label: "Region", value: String(order.DESTINATION_REGION) },
    { icon: Factory, label: "Supplier in", value: String(order.SUPPLIER_REGION) },
    { icon: History, label: "Past orders", value: num.format(Number(order.HIST_PO_COUNT)) },
    { icon: Timer, label: "Usual lead", value: `${Number(order.SUPPLIER_AVG_LEAD).toFixed(0)} days` },
  ];
  return (
    <div className="space-y-3 rounded-xl border bg-muted/40 p-4">
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="flex items-start gap-2">
            <s.icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{s.label}</div>
              <div className="text-sm font-semibold leading-snug">{s.value}</div>
            </div>
          </div>
        ))}
      </div>
      <div
        className={cn(
          "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
          late ? "border-risk-high/30 bg-risk-high/10" : "border-risk-low/30 bg-risk-low/10",
        )}
      >
        {late ? <XCircle className="size-4 text-risk-high" /> : <CheckCircle2 className="size-4 text-risk-low" />}
        <span className="text-muted-foreground">What actually happened:</span>
        <span className={cn("font-semibold", late ? "text-risk-high" : "text-risk-low")}>
          {late ? "Arrived late or short" : "Arrived on time and in full"}
        </span>
      </div>
    </div>
  );
}

function OrderInputs({ order, edited, onChange }: { order: OrderRecord; edited: string[]; onChange: (k: string, v: string | number) => void }) {
  const numField = (key: string, label: string, icon: typeof Cpu, help: string, step = 1) => (
    <Field key={key} label={label} icon={icon} help={help} changed={edited.includes(key)}>
      <Input
        type="number"
        min={0}
        step={step}
        value={String(order[key])}
        onChange={(e) => onChange(key, e.target.value === "" ? 0 : Number(e.target.value))}
        className="tabular-nums"
      />
    </Field>
  );
  const otif = Math.round(Number(order.HIST_OTIF_RATE) * 100);
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Field label="Retailer" icon={Building2} help="The retailer that placed the order." changed={edited.includes("RETAILER_ID")}>
        <Select items={RETAILERS} value={String(order.RETAILER_ID)} onValueChange={(v) => v && onChange("RETAILER_ID", String(v))}>
          <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>
            {Object.entries(RETAILERS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
          </SelectContent>
        </Select>
      </Field>
      {numField("TOTAL_UNITS", "Units ordered", Package, "Total number of items on the purchase order.", 10)}
      {numField("TOTAL_COST", "Order value ($)", CircleDollarSign, "Wholesale cost of the order.", 100)}
      {numField("DAYS_TO_SHIP", "Days until shipped", Timer, "Days from when the order was placed until the supplier shipped it (from the EDI 856 ship notice).")}
      {numField("DAYS_TO_DELIVER", "Days in transit", Truck, "Days the shipment spends with the carrier before reaching the store or warehouse.")}
      <Field
        label="Supplier OTIF"
        icon={TrendingUp}
        help="Share of this supplier's past orders for this retailer that arrived on time and in full. 80% means 8 out of 10."
        changed={edited.includes("HIST_OTIF_RATE")}
        aside={<span className="font-mono text-xs font-semibold text-foreground">{otif}%</span>}
      >
        <Slider
          className="py-2.5"
          value={[otif]}
          min={0}
          max={100}
          step={1}
          onValueChange={(v) => onChange("HIST_OTIF_RATE", (Array.isArray(v) ? v[0] : v) / 100)}
        />
      </Field>
    </div>
  );
}

function Field({
  label, icon: Icon, help, changed, aside, children,
}: { label: string; icon: typeof Cpu; help: string; changed?: boolean; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
          <Icon className="size-3.5" /> {label}
          {changed && <span className="size-1.5 rounded-full bg-brand" aria-label="changed" />}
        </Label>
        <div className="flex items-center gap-1.5">
          {aside}
          <Tooltip>
            <TooltipTrigger className="text-muted-foreground/70 hover:text-foreground" aria-label={`About ${label}`}>
              <Info className="size-3.5" />
            </TooltipTrigger>
            <TooltipContent>{help}</TooltipContent>
          </Tooltip>
        </div>
      </div>
      {children}
    </div>
  );
}

/* ─────────────────────────── Steps 2 + 3 ─────────────────────────── */

function ResultCard({
  scoring, error, result, order, edited, previous,
}: {
  scoring: boolean;
  error: string | null;
  result: ScoreResult | null;
  order: OrderRecord | null;
  edited: boolean;
  previous: number | null;
}) {
  return (
    <Card className="animate-rise overflow-hidden [animation-delay:40ms]">
      <CardHeader>
        <StepTitle n={2} icon={Gauge} title="Check the risk" />
      </CardHeader>
      <CardContent className="space-y-5">
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Couldn&apos;t reach the scoring service</AlertTitle>
            <AlertDescription className="break-all">{error}</AlertDescription>
          </Alert>
        )}
        {scoring && !result && (
          <div className="space-y-4">
            <Skeleton className="mx-auto h-36 w-64 rounded-t-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}
        {!scoring && !result && !error && (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <div className="grid size-14 place-items-center rounded-full bg-accent text-brand">
              <Gauge className="size-7" />
            </div>
            <p className="text-sm font-semibold">No score yet</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              Pick an order and press <b>Score this order</b>. The model answers in about a second.
            </p>
          </div>
        )}
        {result && order && <ScoreView result={result} order={order} edited={edited} previous={previous} dim={scoring} />}
      </CardContent>
    </Card>
  );
}

function ScoreView({ result, order, edited, previous, dim }: { result: ScoreResult; order: OrderRecord; edited: boolean; previous: number | null; dim: boolean }) {
  const risk = result.results[0].riskProbability;
  const b = band(risk);
  const tone = TONE[b.key];
  const deltaPts = Math.round((risk - NETWORK_FAILURE_RATE) * 100);
  const above = deltaPts > 0;
  const late = wasLate(order);
  const agrees = (risk >= 0.5) === late;
  const BandIcon = tone.icon;

  return (
    <div className={cn("animate-rise space-y-5 transition-opacity", dim && "opacity-50")}>
      <RiskGauge value={risk} />

      <div className="flex flex-wrap items-center justify-center gap-2">
        <Badge className={cn("h-7 gap-1.5 px-3 text-sm font-bold uppercase tracking-wide text-primary-foreground", tone.bg)}>
          <BandIcon /> {b.label}
        </Badge>
        <Badge variant="outline" className={cn("h-7 gap-1 px-2.5 text-xs font-semibold", above ? "text-risk-high" : "text-risk-low")}>
          {above ? <ArrowUpRight /> : <ArrowDownRight />}
          {above ? "+" : ""}
          {deltaPts} pts vs. typical order ({pct(NETWORK_FAILURE_RATE)})
        </Badge>
      </div>

      {previous !== null && Math.round(previous * 100) !== Math.round(risk * 100) && (
        <div className="flex items-center justify-center gap-2 rounded-lg border bg-muted/50 px-3 py-2 text-sm">
          <span className="text-muted-foreground">What-if change:</span>
          <span className={cn("font-mono font-semibold", TONE[band(previous).key].text)}>{pct(previous)}</span>
          <ArrowRight className="size-4 text-muted-foreground" />
          <span className={cn("font-mono font-semibold", tone.text)}>{pct(risk)}</span>
          {risk < previous ? (
            <ArrowDownRight className="size-4 text-risk-low" />
          ) : (
            <ArrowUpRight className="size-4 text-risk-high" />
          )}
        </div>
      )}

      <BandScale value={risk} />

      <div className={cn("flex gap-3 rounded-xl border p-4", tone.soft, tone.border)}>
        <BandIcon className={cn("mt-0.5 size-5 shrink-0", tone.text)} />
        <div className="text-sm">
          <p className="font-semibold">What this means</p>
          <p className="text-muted-foreground">{b.action}</p>
        </div>
      </div>

      {!edited && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {agrees ? <CheckCircle2 className="size-4 text-risk-low" /> : <AlertCircle className="size-4 text-risk-watch" />}
          <span>
            In reality this order {late ? "arrived late or short" : "arrived on time and in full"}.{" "}
            <b className="text-foreground">{agrees ? "The model got it right." : "The model's call differs from what happened."}</b>
          </span>
        </div>
      )}

      <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1"><Cpu className="size-3" /> ML endpoint · {result.latencyMs} ms</span>
        <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1"><Lock className="size-3" /> HTTPS + PAT</span>
      </div>
    </div>
  );
}

function ExplanationCard({ loading, error, explanation }: { loading: boolean; error: string | null; explanation: ExplainResult | null }) {
  return (
    <Card className="animate-rise border-brand/20">
      <CardHeader>
        <StepTitle n={3} icon={Sparkles} title="Why?" />
        <CardDescription>Written by Snowflake Cortex AI from the order details.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" /> Asking the AI assistant…
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        )}
        {error && (
          <Alert>
            <AlertCircle />
            <AlertTitle>The AI explanation isn&apos;t available right now</AlertTitle>
            <AlertDescription className="break-all">{error}</AlertDescription>
          </Alert>
        )}
        {explanation && !loading && (
          <>
            <div className="relative rounded-xl bg-accent/70 p-4 pl-5 text-sm leading-relaxed text-foreground">
              <span className="absolute inset-y-3 left-0 w-1 rounded-full bg-brand" />
              {explanation.text}
            </div>
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Treat it as guidance, not a guarantee.</span>
              <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1"><Sparkles className="size-3" /> Cortex · {explanation.latencyMs} ms</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TechDetails({ result, explanation }: { result: ScoreResult | null; explanation: ExplainResult | null }) {
  const flow = [
    { icon: Laptop, label: "This app", sub: "Next.js on your laptop" },
    { icon: Lock, label: "HTTPS + PAT", sub: "Network policy applies" },
    { icon: Cpu, label: "ML endpoint", sub: "FULFILLMENT_RISK_XGB V2 on SPCS" },
    { icon: Sparkles, label: "Cortex REST API", sub: CORTEX_MODEL },
  ];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {flow.map((f, i) => (
          <div key={f.label} className="flex items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2">
              <f.icon className="size-4 text-brand" />
              <div>
                <div className="text-xs font-semibold text-foreground">{f.label}</div>
                <div className="text-[11px]">{f.sub}</div>
              </div>
            </div>
            {i < flow.length - 1 && <ArrowRight className="size-4 text-muted-foreground/60" />}
          </div>
        ))}
      </div>
      <p className="text-muted-foreground">
        The browser talks only to this app&apos;s server routes; the server holds the Snowflake access token (PAT) and calls the
        Snowflake ML real-time inference endpoint and the Cortex REST API. Sample orders are read with the Snowflake SQL REST API.
      </p>
      {result ? (
        <div className="grid gap-3 lg:grid-cols-2">
          <CodeBlock title={`Request · POST ${result.url}`} body={result.request} />
          <CodeBlock title="Response (output_feature_1 = probability of late or short)" body={result.response} />
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">Score an order to see the raw request and response.</p>
      )}
      {explanation && <p className="font-mono text-[11px] text-muted-foreground">Cortex: POST {explanation.url} · {explanation.latencyMs} ms</p>}
    </div>
  );
}

function CodeBlock({ title, body }: { title: string; body: unknown }) {
  return (
    <div className="min-w-0 space-y-1">
      <div className="truncate font-mono text-[11px] font-semibold text-foreground">{title}</div>
      <pre className="max-h-64 overflow-auto rounded-lg bg-brand-deep p-3 font-mono text-[11px] leading-relaxed text-primary-foreground/90">
        {JSON.stringify(body, null, 2)}
      </pre>
    </div>
  );
}
