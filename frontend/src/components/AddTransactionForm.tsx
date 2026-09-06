import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import styled from "styled-components";
import { z } from "zod";

import { ApiError } from "../lib/api";
import { useAccounts, useCategories, useCreateTransaction } from "../lib/queries";
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

const Amount = styled(Input)`
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

export function AddTransactionForm() {
  const accounts = useAccounts();
  const categories = useCategories();
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

  const accountsForCurrency = useMemo(
    () =>
      (accounts.data ?? []).filter(
        (a) => a.currency === currency && a.is_active && a.is_owned,
      ),
    [accounts.data, currency],
  );

  const categoriesForKind = useMemo(() => {
    const list = (categories.data ?? []).filter((c) => !c.is_archived);
    return kind === "income"
      ? list.filter((c) => c.nature === "income")
      : list.filter((c) => c.nature !== "income");
  }, [categories.data, kind]);

  async function onSubmit(values: FormValues) {
    try {
      await create.mutateAsync({
        amount: values.amount,
        account_id: values.account_id,
        kind: values.kind,
        merchant_clean: values.merchant.trim() || null,
        category_id: values.category_id ? Number(values.category_id) : null,
        date: values.date,
      });
      reset({ ...values, amount: "", merchant: "", category_id: "" });
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
            inputMode="decimal"
            placeholder="0.00"
            aria-label="Amount"
            {...register("amount")}
          />
          {errors.amount && <ErrorText>{errors.amount.message}</ErrorText>}
        </Field>

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

        <Field>
          <FieldLabel>Merchant / description</FieldLabel>
          <Input
            placeholder="e.g. Trader Joe's"
            {...register("merchant")}
          />
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
                {a.name}
              </option>
            ))}
          </Select>
          {errors.account_id && (
            <ErrorText>{errors.account_id.message}</ErrorText>
          )}
        </Field>

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
        <Muted>Split a bill or a card that isn’t yours? Save it, then edit it in Transactions.</Muted>
      </Stack>
    </Card>
  );
}
