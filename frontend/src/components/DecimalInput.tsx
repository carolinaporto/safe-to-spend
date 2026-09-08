import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

import { Input } from "./ui";

/** Normalize a partially-typed amount to a dot-decimal string. Mobile keyboards
 *  in a comma-decimal locale (pt-BR) only offer a comma key, so a typed "12,50"
 *  never matches the `12.50` the API and the validators expect. */
export function normalizeDecimalInput(raw: string): string {
  const s = raw.replace(/\s/g, "");
  if (s.includes(",") && s.includes(".")) {
    // e.g. "1.234,56" — dots group, the comma is the decimal separator
    return s.replace(/\./g, "").replace(",", ".");
  }
  return s.replace(",", ".");
}

/** An `<Input>` for money / rate values: shows the decimal keypad and rewrites a
 *  typed comma to a dot before the change reaches the form. Drop-in replacement
 *  for `<Input inputMode="decimal">` — works with a controlled value/onChange
 *  and with react-hook-form `register()`. */
export const DecimalInput = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(function DecimalInput({ onChange, ...props }, ref) {
  return (
    <Input
      ref={ref}
      inputMode="decimal"
      onChange={(e) => {
        const next = normalizeDecimalInput(e.target.value);
        if (next !== e.target.value) e.target.value = next;
        onChange?.(e);
      }}
      {...props}
    />
  );
});
