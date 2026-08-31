import type { Currency } from "./types";

const SYMBOL: Record<string, string> = { USD: "$", BRL: "R$" };

/** Format an API money string for display. Keeps the exact cents from the
 *  server; only adds a grouping separator and a currency symbol. */
export function formatMoney(value: string, currency: string = "USD"): string {
  const negative = value.trim().startsWith("-");
  const [whole, cents = "00"] = value.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const symbol = SYMBOL[currency] ?? `${currency} `;
  return `${negative ? "−" : ""}${symbol}${grouped}.${cents.padEnd(2, "0").slice(0, 2)}`;
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function currencyOptions(): Currency[] {
  return ["USD", "BRL"];
}

/** For chart plotting ONLY. Never use the result for money arithmetic that
 *  gets sent back to the server — the backend owns all financial math. */
export function toPlotNumber(value: string): number {
  return Number.parseFloat(value);
}

export function shortMonth(iso: string): string {
  const [y, m] = iso.slice(0, 7).split("-");
  const names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${names[Number(m) - 1]} ${y.slice(2)}`;
}
