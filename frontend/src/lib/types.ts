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

export type TrafficLight = "green" | "warning" | "danger";

export interface DashboardOverview {
  as_of: string;
  academic_year_end: string;
  net_worth_usd: string;
  emergency_reserve_usd: string;
  future_committed_costs_usd: string;
  available_usd: string;
  months_remaining: string;
  monthly_ceiling_usd: string;
  mtd_spend_usd: string;
  remaining_month_usd: string;
  days_remaining_in_month: number;
  daily_allowance_usd: string;
  projected_month_end_spend_usd: string;
  traffic_light: TrafficLight;
  runway_days: number | null;
  month_progress: { elapsed_days: number; total_days: number };
}

export interface CategorySpend {
  category_id: number | null;
  name: string;
  nature: CategoryNature | null;
  color: string;
  amount_usd: string;
}

export interface ByCategory {
  date_from: string;
  date_to: string;
  categories: CategorySpend[] | null;
  months: { month: string; categories: CategorySpend[] }[] | null;
}

export interface CashflowMonth {
  month: string;
  essential: string;
  discretionary: string;
  setup: string;
  fee: string;
  uncategorized: string;
  total_spend: string;
  income: string;
}

export interface ProjectionPoint {
  date: string;
  balance_usd: string;
}

export interface Projection {
  points: ProjectionPoint[];
  committed_costs: { due_date: string; label: string; amount_usd: string }[];
  daily_burn_usd: string;
  zero_crossing_date: string | null;
}

export interface BudgetLine {
  category_id: number | null;
  name: string;
  nature: CategoryNature | null;
  amount_usd: string;
  rollover: boolean;
  rollover_in_usd: string;
  spent_usd: string;
  remaining_usd: string;
}

export interface MonthBudget {
  month: string;
  lines: BudgetLine[];
}

export interface CommittedCost {
  label: string;
  amount_usd: string;
  due_date: string;
}

export interface PlanConfig {
  academic_year_start: string;
  academic_year_end: string;
  emergency_reserve_usd: string;
  committed_costs: CommittedCost[];
}
