import { createApp } from "./app";
import { connectMongo } from "./config/db";
import { env } from "./config/env";

async function main() {
  await connectMongo();
  const app = createApp();
  app.listen(env.PORT, () => {
    console.log(`ResearchX server listening on http://127.0.0.1:${env.PORT}`);
  });
}

main().catch((err) => {
  console.error("Failed to start server:", err instanceof Error ? err.message : err);
  process.exit(1);
});
