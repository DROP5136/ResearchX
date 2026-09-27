/**
 * Free ports 5000, 8000, 5173 before starting the stack.
 */
const { execSync } = require("child_process");
const os = require("os");

const PORTS = [5000, 8000, 5173];

function freeWindows(port) {
  try {
    const out = execSync(`netstat -ano | findstr :${port}`, { encoding: "utf8" });
    const pids = new Set();
    for (const line of out.split(/\r?\n/)) {
      if (!line.includes("LISTENING")) continue;
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && /^\d+$/.test(pid) && pid !== "0") pids.add(pid);
    }
    for (const pid of pids) {
      try {
        execSync(`taskkill /F /PID ${pid}`, { stdio: "ignore" });
        console.log(`[ports:free] killed PID ${pid} (port ${port})`);
      } catch {
        /* already gone */
      }
    }
  } catch {
    /* nothing listening */
  }
}

function freeUnix(port) {
  try {
    const out = execSync(`lsof -ti tcp:${port} -sTCP:LISTEN`, { encoding: "utf8" });
    for (const pid of out.split(/\s+/).filter(Boolean)) {
      try {
        process.kill(Number(pid), "SIGKILL");
        console.log(`[ports:free] killed PID ${pid} (port ${port})`);
      } catch {
        /* already gone */
      }
    }
  } catch {
    /* nothing listening */
  }
}

const free = os.platform() === "win32" ? freeWindows : freeUnix;
for (const port of PORTS) free(port);
console.log("[ports:free] ready:", PORTS.join(", "));
