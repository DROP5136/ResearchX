import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider } from "@/features/auth/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { LoginPage } from "@/features/auth/AuthPages";
import { DynamicChart } from "@/features/research/components/charts/DynamicChart";
import { ResearchResultsPage } from "@/features/research/ResearchResultsPage";
import { setToken } from "@/api/client";

vi.mock("@/features/auth/api", () => ({
  login: vi.fn(async () => {
    setToken("t");
    return {
      token: "t",
      user: { id: "1", name: "Test", email: "t@example.com" },
    };
  }),
  register: vi.fn(),
  me: vi.fn(async () => {
    throw new Error("no session");
  }),
  logout: vi.fn(),
}));

vi.mock("@/features/research/api", () => ({
  getResearch: vi.fn(async () => ({
    research: {
      id: "abc",
      projectId: "p1",
      userId: "1",
      query: "Analyze the Indian EV market",
      status: "completed",
      progress: 100,
      fastApiResearchId: "RES_1",
      sources: [{ source_id: "SRC_a", title: "EV Report", url: "https://example.com", domain: "example.com" }],
      claims: [
        {
          claim_id: "CLM_1",
          claim: "EV sales grew",
          verification_status: "supported",
          confidence: 0.8,
          source_ids: ["SRC_a"],
          evidence_ids: ["EVD_1"],
        },
      ],
      contradictions: [
        {
          contradiction_id: "CX_1",
          claim_ids: ["CLM_1"],
          description: "Conflicting growth figures",
          status: "open",
        },
      ],
      analysis: [{ metric: "yoy", analysis_type: "yoy_growth", result: 20, status: "ok" }],
      charts: [
        {
          chart_type: "line",
          title: "YoY",
          x_axis: "year",
          data: [
            { year: "2022", value: 100 },
            { year: "2023", value: 120 },
          ],
          series: ["value"],
        },
      ],
      report: {
        title: "EV Market",
        executive_summary: "Summary text",
        key_findings: ["Finding one"],
        markdown: "# Report\n\nHello [SRC_a](https://example.com)",
        methodology: "Mock methodology",
        limitations: ["Limitation"],
      },
    },
  })),
  saveResearch: vi.fn(),
}));

function wrap(ui: React.ReactNode, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[route]}>
            <Routes>
              <Route path="*" element={ui} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders login form and submits", async () => {
    const user = userEvent.setup();
    wrap(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<div>Dashboard ok</div>} />
      </Routes>,
      "/login"
    );
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/email/i), "t@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(localStorage.getItem("rx_token")).toBe("t"));
    await waitFor(() => expect(screen.getByText(/dashboard ok/i)).toBeInTheDocument());
  });
});

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to login", async () => {
    localStorage.clear();
    wrap(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dash</div>} />
        </Route>
        <Route path="/login" element={<div>Login screen</div>} />
      </Routes>,
      "/dashboard"
    );
    await waitFor(() => expect(screen.getByText(/login screen/i)).toBeInTheDocument());
  });
});

describe("Research results", () => {
  it("renders overview sources claims and charts from mocked API", async () => {
    localStorage.setItem("rx_token", "t");
    const auth = await import("@/features/auth/api");
    vi.mocked(auth.me).mockResolvedValue({
      user: { id: "1", name: "Test", email: "t@example.com" },
    });

    wrap(
      <Routes>
        <Route path="/research/:id" element={<ResearchResultsPage />} />
      </Routes>,
      "/research/abc"
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "EV Market" })).toBeInTheDocument());
    expect(screen.getByText(/Summary text/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /Sources/i }));
    await waitFor(() => expect(screen.getByText(/EV Report/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("tab", { name: /Claims/i }));
    await waitFor(() => expect(screen.getByText(/EV sales grew/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("tab", { name: /Data/i }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "YoY" })).toBeInTheDocument());
  });
});

describe("DynamicChart", () => {
  it("renders chart title from backend spec", () => {
    render(
      <div style={{ width: 400, height: 300 }}>
        <DynamicChart
          chart={{
            chart_type: "bar",
            title: "Market Share",
            x_axis: "vendor",
            data: [
              { vendor: "A", share: 40 },
              { vendor: "B", share: 30 },
            ],
            series: ["share"],
          }}
        />
      </div>
    );
    expect(screen.getByText("Market Share")).toBeInTheDocument();
  });
});
