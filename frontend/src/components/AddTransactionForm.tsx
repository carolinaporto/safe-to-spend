import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import styled from "styled-components";
import { z } from "zod";

import { ApiError } from "../lib/api";
import {
  useAccounts,
  useCategories,
  useCreateTransaction,
  usePeople,
} from "../lib/queries";
import { formatMoney } from "../lib/format";
import { DecimalInput, normalizeDecimalInput } from "./DecimalInput";
import {
  Button,
  Card,
  ErrorText,
  Field,
  FieldLabel,
  Input,
  Muted,
  Select,
  Stack,
} from "./ui";
import { useToast } from "./Toast";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  amount: z.string().regex(/^\d+(\.\d{1,2})?$/, "Amount like 12.50"),
  currency: z.enum(["USD", "BRL"]),
  account_id: z.coerce.number().int().positive("Pick an account"),
  kind: z.enum(["expense", "income"]),
  merchant: z.string(),
  category_id: z.string(),
  date: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

const Amount = styled(DecimalInput)`
  font-size: ${({ theme }) => theme.fontSize.xl};
  text-align: center;
  padding: ${({ theme }) => theme.space.md};
`;

const KindToggle = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${({ theme }) => theme.space.sm};
`;

const KindOption = styled.button<{ $active: boolean }>`
  padding: ${({ theme }) => theme.space.sm};
  border-radius: ${({ theme }) => theme.radius.md};
  border: 1px solid
    ${({ theme, $active }) =>
      $active ? theme.color.primary : theme.color.border};
  background: ${({ theme, $active }) =>
    $active ? theme.color.surfaceRaised : "transparent"};
  color: ${({ theme, $active }) =>
    $active ? theme.color.text : theme.color.textMuted};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;

const Title = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  margin-bottom: ${({ theme }) => theme.space.md};
`;

const SplitBox = styled.div`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: ${({ theme }) => theme.space.md};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

const SplitHead = styled.div`
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

const LinkButton = styled.button`
  border: none;
  background: none;
  padding: 0;
  color: ${({ theme }) => theme.color.primary};
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;

const SplitRow = styled.label`
  display: grid;
  grid-template-columns: auto 1fr 6rem;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

const MyShare = styled.div<{ $bad: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  color: ${({ theme, $bad }) =>
    $bad ? theme.color.danger : theme.color.text};
`;

export function AddTransactionForm() {
  const accounts = useAccounts();
  const categories = useCategories();
  const people = usePeople();
  const create = useCreateTransaction();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      amount: "",
      currency: "USD",
      account_id: 0,
      kind: "expense",
      merchant: "",
      category_id: "",
      date: today(),
    },
  });

  const currency = watch("currency");
  const kind = watch("kind");
  const accountId = Number(watch("account_id"));
  const amountStr = watch("amount");

  // person_id -> that person's share as a string
  const [splitWith, setSplitWith] = useState<Record<number, string>>({});

  const personName = useMemo(() => {
    const m = new Map<number, string>();
    for (const p of people.data ?? []) m.set(p.id, p.name);
    return m;
  }, [people.data]);

  const accountsForCurrency = useMemo(
    () =>
      (accounts.data ?? []).filter(
        (a) =>
          a.currency === currency &&
          a.is_active &&
          (a.is_owned || a.owner_person_id != null),
      ),
    [accounts.data, currency],
  );

  // Someone else's card with no owner set can't be used here (we wouldn't
  // know who you owe) — point the user at Settings instead of hiding it.
  const ownerlessExternal = useMemo(
    () =>
      (accounts.data ?? []).filter(
        (a) =>
          a.currency === currency &&
          a.is_active &&
          !a.is_owned &&
          a.owner_person_id == null,
      ),
    [accounts.data, currency],
  );

  const selectedAccount = useMemo(
    () => (accounts.data ?? []).find((a) => a.id === accountId),
    [accounts.data, accountId],
  );
  const external =
    selectedAccount != null &&
    !selectedAccount.is_owned &&
    selectedAccount.owner_person_id != null;
  const ownerId = selectedAccount?.owner_person_id ?? null;

  const splitters = useMemo(
    () =>
      (people.data ?? []).filter(
        (p) => p.role !== "me" && p.id !== ownerId,
      ),
    [people.data, ownerId],
  );

  // Leaving an external account clears the split.
  useEffect(() => {
    if (!external) setSplitWith({});
  }, [external]);

  const amountNum = Number.parseFloat(amountStr || "0") || 0;
  const splitTotal = Object.values(splitWith).reduce(
    (s, v) => s + (Number.parseFloat(v || "0") || 0),
    0,
  );
  const myShare = amountNum - splitTotal;

  function splitEvenly() {
    const ids = Object.keys(splitWith).map(Number);
    if (!ids.length || !amountNum) return;
    const per = (amountNum / (ids.length + 1)).toFixed(2);
    setSplitWith(Object.fromEntries(ids.map((id) => [id, per])));
  }

  function toggleSplitter(id: number, on: boolean) {
    setSplitWith((s) => {
      const next = { ...s };
      if (on) next[id] = "";
      else delete next[id];
      return next;
    });
  }

  const categoriesForKind = useMemo(() => {
    const list = (categories.data ?? []).filter((c) => !c.is_archived);
    return kind === "income"
      ? list.filter((c) => c.nature === "income")
      : list.filter((c) => c.nature !== "income");
  }, [categories.data, kind]);

  async function onSubmit(values: FormValues) {
    const shares = Object.entries(splitWith)
      .map(([pid, amt]) => ({
        person_id: Number(pid),
        share_amount_usd: amt,
      }))
      .filter((s) => Number.parseFloat(s.share_amount_usd || "0") > 0);

    if (external && splitTotal > amountNum + 0.001) {
      toast.error("The split adds up to more than the amount.");
      return;
    }

    try {
      await create.mutateAsync({
        amount: values.amount,
        account_id: values.account_id,
        kind: external ? "expense" : values.kind,
        merchant_clean: values.merchant.trim() || null,
        category_id: values.category_id ? Number(values.category_id) : null,
        date: values.date,
        ...(external
          ? {
              external_treatment: "owe",
              owed_to_person_id: ownerId,
              shares,
            }
          : {}),
      });
      reset({ ...values, amount: "", merchant: "", category_id: "" });
      setSplitWith({});
    } catch (err) {
      // The query client already toasts the failure; keep an inline note too.
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <Card as="form" onSubmit={handleSubmit(onSubmit)}>
      <Title>Add a transaction</Title>
      <Stack $gap="md">
        <Field>
          <Amount
            placeholder="0.00"
            aria-label="Amount"
            {...register("amount")}
          />
          {errors.amount && <ErrorText>{errors.amount.message}</ErrorText>}
        </Field>

        {!external && (
          <KindToggle>
            <KindOption
              type="button"
              $active={kind === "expense"}
              onClick={() => setValue("kind", "expense")}
            >
              Expense
            </KindOption>
            <KindOption
              type="button"
              $active={kind === "income"}
              onClick={() => setValue("kind", "income")}
            >
              Income
            </KindOption>
          </KindToggle>
        )}

        <Field>
          <FieldLabel>Merchant / description</FieldLabel>
          <Input placeholder="e.g. Trader Joe's" {...register("merchant")} />
        </Field>

        <Field>
          <FieldLabel htmlFor="add-currency">Currency</FieldLabel>
          <Select id="add-currency" {...register("currency")}>
            <option value="USD">USD</option>
            <option value="BRL">BRL</option>
          </Select>
        </Field>

        <Field>
          <FieldLabel htmlFor="add-account">Account</FieldLabel>
          <Select id="add-account" {...register("account_id")}>
            <option value={0}>Select…</option>
            {accountsForCurrency.map((a) => (
              <option key={a.id} value={a.id}>
                {a.is_owned || a.owner_person_id == null
                  ? a.name
                  : `${a.name} · ${personName.get(a.owner_person_id) ?? "someone"}'s card`}
              </option>
            ))}
          </Select>
          {errors.account_id && (
            <ErrorText>{errors.account_id.message}</ErrorText>
          )}
          {ownerlessExternal.map((a) => (
            <Muted key={a.id}>
              {a.name} needs an owner — set whose card it is in Settings →
              Accounts (add the person in People first).
            </Muted>
          ))}
        </Field>

        {external && ownerId != null && (
          <SplitBox>
            <SplitHead>
              <span>
                You’ll owe {personName.get(ownerId) ?? "the owner"} the full{" "}
                {formatMoney(String(amountNum || 0), "USD")}. Who splits it?
              </span>
              {Object.keys(splitWith).length > 0 && (
                <LinkButton type="button" onClick={splitEvenly}>
                  Split evenly
                </LinkButton>
              )}
            </SplitHead>
            {splitters.length === 0 && (
              <Muted>Add roommates in People to split with them.</Muted>
            )}
            {splitters.map((p) => {
              const on = p.id in splitWith;
              return (
                <SplitRow key={p.id}>
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={(e) => toggleSplitter(p.id, e.target.checked)}
                  />
                  <span>{p.name}</span>
                  <Input
                    inputMode="decimal"
                    aria-label={`${p.name}'s share`}
                    placeholder="0.00"
                    disabled={!on}
                    value={splitWith[p.id] ?? ""}
                    onChange={(e) =>
                      setSplitWith((s) => ({
                        ...s,
                        [p.id]: normalizeDecimalInput(e.target.value),
                      }))
                    }
                  />
                </SplitRow>
              );
            })}
            <MyShare $bad={myShare < -0.001}>
              Your share: {formatMoney(myShare.toFixed(2), "USD")}
            </MyShare>
          </SplitBox>
        )}

        <Field>
          <FieldLabel htmlFor="add-category">Category</FieldLabel>
          <Select id="add-category" {...register("category_id")}>
            <option value="">Uncategorized</option>
            {categoriesForKind.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field>
          <FieldLabel htmlFor="add-date">Date</FieldLabel>
          <Input id="add-date" type="date" {...register("date")} />
        </Field>

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Add"}
        </Button>

        {accountsForCurrency.length === 0 && (
          <Muted>No active {currency} account — add one in Settings.</Muted>
        )}
      </Stack>
    </Card>
  );
}
