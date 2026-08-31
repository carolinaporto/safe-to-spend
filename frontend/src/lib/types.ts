// Money and FX rates arrive from the API as strings (never floats) and are
// rendered as-is or formatted for display — never parsed into a JS number
// for arithmetic.

export type AccountKind =
  | "checking"
  | "savings"
  | "credit_card"
  | "cash"
  | "external";

export type Currency = "USD" | "BRL";

export type CategoryNature =
  | "essential"
  | "discretionary"
  | "setup"
  | "fee"
  | "income";

export type TransactionKind = "expense" | "income" | "transfer" | "adjustment";
export type TransactionDirection = "in" | "out";

export interface Account {
  id: number;
  name: string;
  institution: string;
  kind: AccountKind;
  currency: Currency;
  opening_balance: string;
  opening_date: string;
  statement_day: number | null;
  due_day: number | null;
  color: string;
  icon: string;
  is_active: boolean;
  sort_order: number;
  is_owned: boolean;
  balance: string;
  balance_usd: string;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  nature: CategoryNature;
  icon: string;
  color: string;
  is_archived: boolean;
}

export interface Transaction {
  id: number;
  date: string;
  account_id: number;
  direction: TransactionDirection;
  kind: TransactionKind;
  amount: string;
  currency: string;
  fx_rate_to_usd: string;
  amount_usd: string;
  category_id: number | null;
  merchant_raw: string | null;
  merchant_clean: string | null;
  description: string;
  notes: string;
  is_shared: boolean;
  is_reimbursable: boolean;
  excluded_from_my_budget: boolean;
  source: string;
  needs_review: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface AccountBalance {
  id: number;
  name: string;
  institution: string;
  currency: Currency;
  kind: AccountKind;
  is_owned: boolean;
  balance: string;
  balance_usd: string;
}

export interface DashboardBalances {
  net_worth_usd: string;
  accounts: AccountBalance[];
}
