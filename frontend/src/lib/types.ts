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
export type PersonRole = "me" | "roommate" | "parent" | "other";
export type RecurringFrequency = "weekly" | "monthly" | "yearly";
export type ExternalTreatment = "gift" | "owe";

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
  owner_person_id: number | null;
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
  transfer_group_id: string | null;
  shares: ExpenseShare[];
  created_at: string;
  updated_at: string;
}

export interface ExpenseShare {
  id: number;
  person_id: number;
  share_amount_usd: string;
  settled: boolean;
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
  is_active: boolean;
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
  future_recurring_costs_usd: string;
  available_usd: string;
  months_remaining: string;
  monthly_ceiling_usd: string;
  mtd_spend_usd: string;
  remaining_month_usd: string;
  days_remaining_in_month: number;
  daily_rate_usd: string;
  daily_allowance_usd: string;
  projected_month_end_spend_usd: string;
  traffic_light: TrafficLight;
  runway_days: number | null;
  receivables_usd: string;
  liabilities_usd: string;
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

export interface MonthSummary {
  month: string;
  is_current: boolean;
  spent_usd: string;
  scheduled_usd: string;
  categories: CategorySpend[];
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

// ---------------------------------------------------------------- import

export type MerchantMatchType = "contains" | "regex";
export type ImportRowStatus = "new" | "duplicate" | "uncategorized";

export interface MerchantRule {
  id: number;
  pattern: string;
  match_type: MerchantMatchType;
  category_id: number | null;
  merchant_clean: string | null;
  priority: number;
  hit_count: number;
}

export interface PreviewRow {
  key: string;
  date: string;
  amount: string;
  direction: TransactionDirection;
  currency: string;
  merchant_raw: string;
  merchant_clean: string | null;
  category_id: number | null;
  category_name: string | null;
  amount_usd: string;
  fx_stale: boolean;
  status: ImportRowStatus;
  external_id: string | null;
}

export interface ImportPreview {
  parser: string;
  account_id: number;
  filename: string;
  rows: PreviewRow[];
  summary: { total: number; new: number; duplicate: number; uncategorized: number };
}

export interface ImportCommitResult {
  batch_id: number;
  parser: string;
  filename: string;
  row_count: number;
  imported_count: number;
  duplicate_count: number;
}

export interface ReviewItem {
  id: number;
  date: string;
  account_id: number;
  amount: string;
  currency: string;
  amount_usd: string;
  merchant_raw: string | null;
  merchant_clean: string | null;
  description: string;
  category_id: number | null;
  direction: TransactionDirection;
  kind: TransactionKind;
  source: string;
}

export interface ReviewQueue {
  items: ReviewItem[];
  total: number;
}

// ------------------------------------------------------------- phase 4

export interface Person {
  id: number;
  name: string;
  role: PersonRole;
  notes: string;
}

export interface PersonBalance {
  person_id: number;
  name: string;
  role: PersonRole;
  owed_to_me_usd: string;
  i_owe_usd: string;
  net_usd: string;
}

export interface Transfer {
  id: number;
  transfer_group_id: string;
  date: string;
  from_account_id: number;
  to_account_id: number;
  amount_out: string;
  currency_out: string;
  amount_in: string;
  currency_in: string;
  explicit_fee: string | null;
  explicit_fee_currency: string | null;
  effective_rate: string;
  market_rate: string;
  fx_cost_usd: string;
  provider: string;
  notes: string;
}

export interface ProviderSummary {
  provider: string;
  count: number;
  fx_cost_usd: string;
  avg_effective_rate: string;
}

export interface TransferSummary {
  count: number;
  total_fx_cost_usd: string;
  providers: ProviderSummary[];
}

export interface RecurringRule {
  id: number;
  name: string;
  account_id: number;
  category_id: number | null;
  amount: string;
  currency: string;
  frequency: RecurringFrequency;
  day_of_month: number;
  start_date: string;
  end_date: string | null;
  auto_create: boolean;
  is_income: boolean;
  last_generated_date: string | null;
}

export interface IncomeEntry {
  id: number;
  date: string;
  account_id: number;
  amount: string;
  currency: string;
  amount_usd: string;
}

export interface IncomeSummary {
  total_funding_brl: string;
  total_funding_usd: string;
  converted_brl: string;
  converted_usd: string;
  still_in_brl: string;
  still_in_brl_usd: string;
  cumulative_fx_cost_usd: string;
  entries: IncomeEntry[];
}

export interface CardPanel {
  account_id: number;
  name: string;
  currency: string;
  current_balance_usd: string;
  statement_balance_usd: string;
  statement_close_date: string | null;
  due_date: string | null;
  days_until_due: number | null;
  alert: boolean;
}
