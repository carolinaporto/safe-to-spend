import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { useAuth } from "./auth/AuthContext";
import { Budget } from "./pages/Budget";
import { Home } from "./pages/Home";
import { Import } from "./pages/Import";
import { Income } from "./pages/Income";
import { Login } from "./pages/Login";
import { People } from "./pages/People";
import { Settings } from "./pages/Settings";
import { Transactions } from "./pages/Transactions";
import { Transfers } from "./pages/Transfers";

export function App() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="import" element={<Import />} />
        <Route path="transfers" element={<Transfers />} />
        <Route path="budget" element={<Budget />} />
        <Route path="people" element={<People />} />
        <Route path="income" element={<Income />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
