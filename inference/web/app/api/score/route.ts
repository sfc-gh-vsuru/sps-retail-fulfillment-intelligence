import { score } from "@/lib/server/snowflake";
import type { OrderRecord } from "@/lib/model";

// Body: { record: OrderRecord } -> Snowflake ML real-time inference endpoint
export async function POST(request: Request) {
  try {
    const { record } = (await request.json()) as { record: OrderRecord };
    return Response.json(await score([record]));
  } catch (err) {
    console.error("score:", err);
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
}
