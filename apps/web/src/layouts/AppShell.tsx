import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Bookmark,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Plus,
  Search,
  Settings,
  Sun,
  X,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/research/new", label: "Research", icon: Search },
  { to: "/saved-reports", label: "Saved Reports", icon: Bookmark },
  { to: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-[260px] border-r border-ink-200/70 bg-white/90 p-4 backdrop-blur-md transition-transform dark:border-ink-800 dark:bg-ink-950/90 lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="mb-8 flex items-center justify-between px-2">
          <Link to="/dashboard" className="font-display text-2xl tracking-tight text-ink-950 dark:text-white">
            Research<span className="text-accent">X</span>
          </Link>
          <button type="button" className="rx-btn-ghost lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-1" aria-label="Main">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                  isActive
                    ? "bg-accent/10 text-accent-muted dark:bg-accent/15 dark:text-accent-soft"
                    : "text-ink-600 hover:bg-ink-100/80 dark:text-ink-300 dark:hover:bg-ink-800/60"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button
          type="button"
          className="rx-btn-primary mt-6 w-full"
          onClick={() => {
            setOpen(false);
            navigate("/research/new");
          }}
        >
          <Plus className="h-4 w-4" />
          Start Research
        </button>
      </aside>

      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-ink-950/40 lg:hidden"
          aria-label="Close overlay"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-ink-200/70 bg-white/70 px-4 py-3 backdrop-blur-md dark:border-ink-800 dark:bg-ink-950/70 sm:px-6">
          <div className="flex items-center gap-2">
            <button type="button" className="rx-btn-ghost lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="font-display text-lg leading-none text-ink-950 dark:text-white">ResearchX</p>
              <p className="text-xs text-ink-500">Multi-agent research intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="rx-btn-ghost" onClick={toggle} aria-label="Toggle theme">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-ink-500">{user?.email}</p>
            </div>
            <button
              type="button"
              className="rx-btn-secondary"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
