// The single source of truth for every colour, spacing, radius, shadow and
// type value in the app. No styled component may hardcode a hex or a length
// value that could live here instead.
//
// Spacing and type are in `rem`, so the whole UI scales with the root
// font-size — which GlobalStyle shrinks on small screens.

export const theme = {
  color: {
    // Surfaces
    bg: "#0f1115",
    surface: "#171a21",
    surfaceRaised: "#1e222b",
    border: "#2b303b",

    // Text
    text: "#e7e9ee",
    textMuted: "#9aa2b1",
    textFaint: "#6b7280",

    // Brand / interactive
    primary: "#4f8cff",
    primaryHover: "#3d78e8",
    primaryText: "#ffffff",

    // Traffic-light semantic tokens (spec section 1)
    success: "#3fb950",
    warning: "#d29922",
    danger: "#f85149",

    // Money direction
    inflow: "#3fb950",
    outflow: "#f85149",

    focusRing: "#4f8cff",
  },

  // Per-category-nature colours (spec section 3: essential/discretionary/setup/fee/income)
  nature: {
    essential: "#4f8cff",
    discretionary: "#a371f7",
    setup: "#f0883e",
    fee: "#d29922",
    income: "#3fb950",
  },

  // Distinct palette for per-category charts (donut/bars) so slices are
  // told apart regardless of nature. Category-specific `color` overrides it.
  chartPalette: [
    "#4f8cff",
    "#f0883e",
    "#3fb950",
    "#a371f7",
    "#ec6cb9",
    "#39c5cf",
    "#d29922",
    "#f85149",
    "#2dd4bf",
    "#fb7185",
    "#a3e635",
    "#c084fc",
    "#60a5fa",
    "#fbbf24",
  ],

  // Spacing scale, in rem (0.25rem = 4px at a 16px root).
  space: {
    none: "0",
    xxs: "0.125rem",
    xs: "0.25rem",
    sm: "0.5rem",
    md: "0.75rem",
    lg: "1rem",
    xl: "1.5rem",
    xxl: "2rem",
    xxxl: "3rem",
  },

  radius: {
    sm: "0.25rem",
    md: "0.5rem",
    lg: "0.75rem",
    pill: "999px",
  },

  font: {
    body: '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    mono: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
  },

  fontSize: {
    xs: "0.75rem",
    sm: "0.8125rem",
    md: "0.9375rem",
    lg: "1.125rem",
    xl: "1.5rem",
    xxl: "2rem",
    display: "2.75rem",
  },

  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.2,
    normal: 1.5,
  },

  shadow: {
    sm: "0 1px 2px rgba(0, 0, 0, 0.4)",
    md: "0 4px 12px rgba(0, 0, 0, 0.35)",
    lg: "0 12px 32px rgba(0, 0, 0, 0.45)",
  },

  layout: {
    sidebarWidth: "14.5rem",
    contentMaxWidth: "70rem",
    bottomNavHeight: "3.75rem",
  },

  // Media-query breakpoints, in em (respect the user's zoom / font settings).
  bp: {
    sm: "37.5em", // ~600px — collapse multi-column forms
    md: "48em", //   ~768px — switch to the mobile nav
    lg: "64em", //   ~1024px — collapse the dashboard side column
  },

  transition: {
    fast: "120ms ease",
    base: "200ms ease",
  },
} as const;

export type Theme = typeof theme;
