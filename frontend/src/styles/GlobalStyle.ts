import { createGlobalStyle } from "styled-components";

export const GlobalStyle = createGlobalStyle`
  *, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  /* Everything is sized in rem; shrink the root on small screens so the
     whole UI scales down together. */
  :root {
    font-size: 16px;
  }
  @media (max-width: ${({ theme }) => theme.bp.md}) {
    :root { font-size: 15px; }
  }
  @media (max-width: 24em) {
    :root { font-size: 14px; }
  }

  html, body, #root {
    height: 100%;
  }

  body {
    background: ${({ theme }) => theme.color.bg};
    color: ${({ theme }) => theme.color.text};
    font-family: ${({ theme }) => theme.font.body};
    font-size: ${({ theme }) => theme.fontSize.md};
    line-height: ${({ theme }) => theme.lineHeight.normal};
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
    overflow-x: hidden;
  }

  /* Long unbroken strings (merchant names, URLs) must never widen the page. */
  p, span, strong, td, th, div, h1, h2, h3, h4, a, button {
    overflow-wrap: break-word;
  }

  img, svg, video, canvas {
    max-width: 100%;
    height: auto;
  }

  h1, h2, h3, h4 {
    line-height: ${({ theme }) => theme.lineHeight.tight};
    font-weight: ${({ theme }) => theme.fontWeight.semibold};
  }

  a {
    color: inherit;
    text-decoration: none;
  }

  button, input, select, textarea {
    font: inherit;
    color: inherit;
  }

  /* iOS zooms a focused field whose text is < 16px — pin form text to 16px
     on small screens where the root is smaller. */
  @media (max-width: ${({ theme }) => theme.bp.md}) {
    input, select, textarea {
      font-size: 16px;
    }
  }

  :focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.focusRing};
    outline-offset: 2px;
  }

  code, pre {
    font-family: ${({ theme }) => theme.font.mono};
  }
`;
