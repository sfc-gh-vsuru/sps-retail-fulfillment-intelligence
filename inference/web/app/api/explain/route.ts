import { explain } from "@/lib/server/snowflake";
import type { OrderRecord } from "@/lib/model";

// Body: { record: OrderRecord, riskProbability: number } -> Cortex REST API
export async function POST(request: Request) {
  try {
    const { record, riskProbability } = (await request.json()) as { record: OrderRecord; riskProbability: number };
    return Response.json(await explain(record, Number(riskProbability)));
  } catch (err) {
    console.error("explain:", err);
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
}
