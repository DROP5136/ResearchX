/**
 * Start FastAPI AI service using the repo .venv (Windows or Unix).
 */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const aiDir = path.join(root, "apps", "ai-service");
const winPy = path.join(root, ".venv", "Scripts", "python.exe");
const unixPy = path.join(root, ".venv", "bin", "python");
const python = fs.existsSync(winPy) ? winPy : unixPy;

if (!fs.existsSync(python)) {
  console.error(
    "[dev:ai] Python venv not found. Create it and install deps:\n" +
      "  python -m venv .venv\n" +
      "  .\\.venv\\Scripts\\Activate.ps1\n" +
      "  pip install -r apps/ai-service/requirements.txt"
  );
  process.exit(1);
}

const child = spawn(
  python,
  ["-m", "uvicorn", "app.api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
  {
    cwd: aiDir,
    stdio: "inherit",
    env: process.env,
    shell: false,
  }
);

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});

process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
