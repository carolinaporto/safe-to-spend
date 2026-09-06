import { IconContext } from "@phosphor-icons/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "styled-components";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ToastProvider } from "./components/Toast";
import { queryClient } from "./lib/queryClient";
import { GlobalStyle } from "./styles/GlobalStyle";
import { theme } from "./theme";

// One icon weight for the whole app (spec section 1).
const iconContext = { weight: "duotone" as const, size: 20 };

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <IconContext.Provider value={iconContext}>
        <GlobalStyle />
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <ToastProvider>
                <App />
              </ToastProvider>
            </AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </IconContext.Provider>
    </ThemeProvider>
  </StrictMode>,
);
