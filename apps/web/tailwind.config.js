/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f4f7f8",
          100: "#e3eaed",
          200: "#c5d3d9",
          300: "#9db3bd",
          400: "#6e8d9b",
          500: "#537280",
          600: "#455d6b",
          700: "#3b4e59",
          800: "#34434c",
          900: "#2e3a42",
          950: "#1a2329",
        },
        accent: {
          DEFAULT: "#0d9488",
          soft: "#14b8a6",
          muted: "#0f766e",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"DM Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(15, 23, 42, 0.04), 0 12px 40px rgba(15, 23, 42, 0.06)",
      },
      backgroundImage: {
        "atmosphere-light":
          "radial-gradient(1200px 600px at 10% -10%, rgba(13,148,136,0.12), transparent 55%), radial-gradient(900px 500px at 100% 0%, rgba(83,114,128,0.10), transparent 50%), linear-gradient(180deg, #f7fafb 0%, #eef3f5 100%)",
        "atmosphere-dark":
          "radial-gradient(1000px 500px at 0% 0%, rgba(20,184,166,0.12), transparent 50%), radial-gradient(800px 400px at 100% 10%, rgba(83,114,128,0.18), transparent 45%), linear-gradient(180deg, #12181c 0%, #1a2329 100%)",
      },
    },
  },
  plugins: [],
};
