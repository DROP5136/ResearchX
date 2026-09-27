import { createApp } from "./app";
import { connectMongo } from "./config/db";
import { env } from "./config/env";

async function main() {
  await connectMongo();
  const app = createApp();
  const host = env.HOST || "0.0.0.0";
  app.listen(env.PORT, host, () => {
    console.log(`ResearchX server listening on ${host}:${env.PORT}`);
  });
}

main().catch((err) => {
  console.error("Failed to start server:", err instanceof Error ? err.message : err);
  process.exit(1);
});
