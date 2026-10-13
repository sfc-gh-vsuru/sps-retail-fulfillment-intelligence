# SPS PO Risk Checker (web app)

Next.js + shadcn/ui front end for the inference add-on. Server routes call the Snowflake ML real-time inference endpoint, the Cortex REST API, and the SQL REST API with the PAT from `../.env` / `~/.snowflake/connections.toml`. The token never reaches the browser.

```bash
npm install
npm run dev     # http://localhost:3000
```

Full docs: [../INFERENCE_README.md](../INFERENCE_README.md#web-app-react) · Setup: [../INFERENCE_SETUP.md](../INFERENCE_SETUP.md) · Talk track: [../INFERENCE_DEMO_TALK_TRACK.md](../INFERENCE_DEMO_TALK_TRACK.md)
