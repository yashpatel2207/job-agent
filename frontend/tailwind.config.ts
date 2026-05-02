import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        snow: "hsl(var(--snow) / <alpha-value>)",
        "snow-2": "hsl(var(--snow-2) / <alpha-value>)",
        paper: "hsl(var(--paper) / <alpha-value>)",
        ink: "hsl(var(--ink) / <alpha-value>)",
        slate: "hsl(var(--slate) / <alpha-value>)",
        mute: "hsl(var(--mute) / <alpha-value>)",
        hairline: "hsl(var(--hairline) / <alpha-value>)",
        blue: "hsl(var(--blue) / <alpha-value>)",
        "blue-2": "hsl(var(--blue-2) / <alpha-value>)",
        amber: "hsl(var(--amber) / <alpha-value>)",
        green: "hsl(var(--green) / <alpha-value>)",
        red: "hsl(var(--red) / <alpha-value>)",
        teal: "hsl(var(--teal) / <alpha-value>)",
        coral: "hsl(var(--coral) / <alpha-value>)",
        indigo: "hsl(var(--indigo) / <alpha-value>)",
        // Pastel surface tints
        mint: "hsl(var(--mint-bg) / <alpha-value>)",
        butter: "hsl(var(--butter-bg) / <alpha-value>)",
        peach: "hsl(var(--peach-bg) / <alpha-value>)",
        sky: "hsl(var(--sky-bg) / <alpha-value>)",
        lavender: "hsl(var(--lavender-bg) / <alpha-value>)",
        // legacy aliases — keep so any unmodified utility still resolves
        border: "hsl(var(--border) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        // legacy aliases pointing at new palette so old class names keep working
        bone: "hsl(var(--ink) / <alpha-value>)",
        ash: "hsl(var(--slate) / <alpha-value>)",
        ember: "hsl(var(--blue) / <alpha-value>)",
        gold: "hsl(var(--amber) / <alpha-value>)",
        sage: "hsl(var(--green) / <alpha-value>)",
        crimson: "hsl(var(--red) / <alpha-value>)",
        rule: "hsl(var(--hairline) / <alpha-value>)",
        "rule-strong": "hsl(var(--hairline) / <alpha-value>)",
      },
      fontFamily: {
        display: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.022em",
        snug: "-0.015em",
      },
      borderRadius: {
        pill: "980px",
      },
      boxShadow: {
        soft: "0 1px 3px rgb(0 0 0 / 0.04), 0 8px 24px -8px rgb(0 0 0 / 0.06)",
        lift: "0 1px 3px rgb(0 0 0 / 0.05), 0 16px 36px -8px rgb(0 0 0 / 0.10)",
        ring: "0 0 0 4px hsl(var(--blue) / 0.18)",
      },
      animation: {
        reveal: "reveal 0.7s cubic-bezier(0.2, 0.7, 0.2, 1) forwards",
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
      },
      keyframes: {
        reveal: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
}
export default config
