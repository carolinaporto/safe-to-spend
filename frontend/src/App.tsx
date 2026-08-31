import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import {
  Budget,
  Home,
  Income,
  People,
  QuickAdd,
  Settings,
  Transactions,
  Transfers,
} from "./pages/placeholders";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="quick-add" element={<QuickAdd />} />
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
