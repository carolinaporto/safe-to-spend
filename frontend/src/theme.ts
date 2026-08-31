// The single source of truth for every colour, spacing, radius, shadow and
// type value in the app. No styled component may hardcode a hex or a pixel
// value that could live here instead.

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

  // 4px base spacing scale
  space: {
    none: "0",
    xxs: "2px",
    xs: "4px",
    sm: "8px",
    md: "12px",
    lg: "16px",
    xl: "24px",
    xxl: "32px",
    xxxl: "48px",
  },

  radius: {
    sm: "4px",
    md: "8px",
    lg: "12px",
    pill: "999px",
  },

  font: {
    body: '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    mono: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
  },

  fontSize: {
    xs: "12px",
    sm: "13px",
    md: "15px",
    lg: "18px",
    xl: "24px",
    xxl: "32px",
    display: "44px",
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
    sidebarWidth: "232px",
    contentMaxWidth: "1120px",
  },

  transition: {
    fast: "120ms ease",
    base: "200ms ease",
  },
} as const;

export type Theme = typeof theme;
