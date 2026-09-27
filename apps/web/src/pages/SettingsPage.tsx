import { useAuth } from "@/features/auth/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";

export function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink-950 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-ink-500">Profile and application preferences. Backend secrets are never exposed here.</p>
      </div>

      <section className="rx-panel space-y-3 p-5">
        <h2 className="font-display text-xl">Profile</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="rx-label">Name</dt>
            <dd>{user?.name}</dd>
          </div>
          <div>
            <dt className="rx-label">Email</dt>
            <dd>{user?.email}</dd>
          </div>
        </dl>
      </section>

      <section className="rx-panel space-y-3 p-5">
        <h2 className="font-display text-xl">Theme</h2>
        <div className="flex gap-2">
          <button type="button" className={theme === "light" ? "rx-btn-primary" : "rx-btn-secondary"} onClick={() => setTheme("light")}>
            Light
          </button>
          <button type="button" className={theme === "dark" ? "rx-btn-primary" : "rx-btn-secondary"} onClick={() => setTheme("dark")}>
            Dark
          </button>
        </div>
      </section>

      <section className="rx-panel space-y-2 p-5 text-sm text-ink-500">
        <h2 className="font-display text-xl text-ink-900 dark:text-ink-100">Preferences</h2>
        <p>Research defaults (mock mode, depth) are chosen per run on the New Research page.</p>
        <p>API base URL is configured via <code className="font-mono">VITE_API_URL</code> only.</p>
      </section>
    </div>
  );
}
