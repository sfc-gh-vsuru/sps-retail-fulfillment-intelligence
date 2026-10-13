import { connection } from "next/server";
import { fetchSamples } from "@/lib/server/snowflake";

// Real historical POs from SPS_RETAIL_AI.ML_INFERENCE.SAMPLE_REQUESTS (via the SQL REST API).
export async function GET() {
  await connection();
  try {
    return Response.json(await fetchSamples());
  } catch (err) {
    console.error("samples:", err);
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
}
