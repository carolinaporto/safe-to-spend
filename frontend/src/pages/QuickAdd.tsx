import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import styled from "styled-components";
import { z } from "zod";

import {
  Button,
  Card,
  ErrorText,
  Field,
  FieldLabel,
  GhostButton,
  Input,
  Muted,
  PageTitle,
  Row,
  Select,
  Stack,
} from "../components/ui";
import { ApiError } from "../lib/api";
import { formatMoney } from "../lib/format";
import {
  useAccounts,
  useCategories,
  useCreateTransaction,
  usePeople,
} from "../lib/queries";
import type { ExternalTreatment } from "../lib/types";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  amount: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, "Enter an amount like 12.50"),
  currency: z.enum(["USD", "BRL"]),
  account_id: z.coerce.number().int().positive("Pick an account"),
  kind: z.enum(["expense", "income"]),
  category_id: z.string(),
  date: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

const Screen = styled.div`
  max-width: 460px;
  margin: 0 auto;
`;

const Amount = styled(Input)`
  font-size: ${({ theme }) => theme.fontSize.xxl};
  text-align: center;
  padding: ${({ theme }) => theme.space.lg};
`;

const KindToggle = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${({ theme }) => theme.space.sm};
`;

const KindOption = styled.button<{ $active: boolean }>`
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.md};
  border: 1px solid
    ${({ theme, $active }) =>
      $active ? theme.color.primary : theme.color.border};
  background: ${({ theme, $active }) =>
    $active ? theme.color.surfaceRaised : "transparent"};
  color: ${({ theme, $active }) =>
    $active ? theme.color.text : theme.color.textMuted};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  cursor: pointer;
`;

const Saved = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  color: ${({ theme }) => theme.color.success};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

interface Split {
  person_id: string;
  share_amount_usd: string;
}

export function QuickAdd() {
  const accounts = useAccounts();
  const categories = useCategories();
  const people = usePeople();
  const create = useCreateTransaction();
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [splits, setSplits] = useState<Split[]>([]);
  const [treatment, setTreatment] = useState<ExternalTreatment>("owe");
  const [oweTo, setOweTo] = useState("");

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
      category_id: "",
      date: today(),
    },
  });

  const currency = watch("currency");
  const kind = watch("kind");
  const accountId = watch("account_id");

  const accountsForCurrency = useMemo(
    () =>
      (accounts.data ?? []).filter(
        (a) => a.currency === currency && a.is_active,
      ),
    [accounts.data, currency],
  );

  const selectedAccount = (accounts.data ?? []).find(
    (a) => a.id === Number(accountId),
  );
  const isExternal = selectedAccount?.kind === "external";
  const otherPeople = (people.data ?? []).filter((p) => p.role !== "me");

  const categoriesForKind = useMemo(() => {
    const list = (categories.data ?? []).filter((c) => !c.is_archived);
    return kind === "income"
      ? list.filter((c) => c.nature === "income")
      : list.filter((c) => c.nature !== "income");
  }, [categories.data, kind]);

  async function onSubmit(values: FormValues) {
    setSubmitError(null);
    const extra: Record<string, unknown> = {};
    if (isExternal && values.kind === "expense") {
      extra.external_treatment = treatment;
      if (treatment === "owe" && oweTo) extra.owed_to_person_id = Number(oweTo);
    } else if (values.kind === "expense" && splits.length > 0) {
      extra.is_shared = true;
      extra.shares = splits
        .filter((s) => s.person_id && s.share_amount_usd)
        .map((s) => ({
          person_id: Number(s.person_id),
          share_amount_usd: s.share_amount_usd,
        }));
    }
    try {
      await create.mutateAsync({
        amount: values.amount,
        account_id: values.account_id,
        kind: values.kind,
        category_id: values.category_id ? Number(values.category_id) : null,
        date: values.date,
        ...extra,
      });
      setLastSaved(
        `${formatMoney(values.amount, values.currency)} — ${values.kind}`,
      );
      setSplits([]);
      setOweTo("");
      reset({
        ...values,
        amount: "",
        category_id: "",
        date: today(),
      });
    } catch (err) {
      setSubmitError(
        err instanceof ApiError ? err.message : "Could not save",
      );
    }
  }

  return (
    <Screen>
      <PageTitle>Quick add</PageTitle>
      <Card>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Stack $gap="lg">
            <Field>
              <Amount
                inputMode="decimal"
                placeholder="0.00"
                autoFocus
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
              <FieldLabel htmlFor="currency">Currency</FieldLabel>
              <Select id="currency" {...register("currency")}>
                <option value="USD">USD</option>
                <option value="BRL">BRL</option>
              </Select>
            </Field>

            <Field>
              <FieldLabel htmlFor="account">Account</FieldLabel>
              <Select id="account" {...register("account_id")}>
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
              <FieldLabel htmlFor="category">Category</FieldLabel>
              <Select id="category" {...register("category_id")}>
                <option value="">Uncategorized</option>
                {categoriesForKind.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>

            {kind === "expense" && isExternal && (
              <Field>
                <FieldLabel>This isn’t my card</FieldLabel>
                <KindToggle>
                  <KindOption
                    type="button"
                    $active={treatment === "gift"}
                    onClick={() => setTreatment("gift")}
                  >
                    It’s a gift
                  </KindOption>
                  <KindOption
                    type="button"
                    $active={treatment === "owe"}
                    onClick={() => setTreatment("owe")}
                  >
                    I owe it back
                  </KindOption>
                </KindToggle>
                {treatment === "owe" && (
                  <Select
                    aria-label="Owe to"
                    value={oweTo}
                    onChange={(e) => setOweTo(e.target.value)}
                  >
                    <option value="">
                      {selectedAccount?.owner_person_id
                        ? "card owner"
                        : "Who do you owe?"}
                    </option>
                    {otherPeople.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </Select>
                )}
                <Muted>
                  {treatment === "gift"
                    ? "Counts in category spending, but not against your budget or balance."
                    : "Counts as your spending and as money you owe them."}
                </Muted>
              </Field>
            )}

            {kind === "expense" && !isExternal && otherPeople.length > 0 && (
              <Field>
                <FieldLabel>Split with someone</FieldLabel>
                <Stack $gap="sm">
                  {splits.map((s, i) => (
                    <Row key={i} $gap="sm">
                      <Select
                        aria-label="Person"
                        value={s.person_id}
                        onChange={(e) =>
                          setSplits(
                            splits.map((x, j) =>
                              j === i
                                ? { ...x, person_id: e.target.value }
                                : x,
                            ),
                          )
                        }
                      >
                        <option value="">Person…</option>
                        {otherPeople.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </Select>
                      <Input
                        inputMode="decimal"
                        placeholder="their share (USD)"
                        value={s.share_amount_usd}
                        onChange={(e) =>
                          setSplits(
                            splits.map((x, j) =>
                              j === i
                                ? { ...x, share_amount_usd: e.target.value }
                                : x,
                            ),
                          )
                        }
                      />
                      <GhostButton
                        type="button"
                        aria-label="Remove split"
                        onClick={() =>
                          setSplits(splits.filter((_, j) => j !== i))
                        }
                      >
                        ×
                      </GhostButton>
                    </Row>
                  ))}
                  <GhostButton
                    type="button"
                    onClick={() =>
                      setSplits([
                        ...splits,
                        { person_id: "", share_amount_usd: "" },
                      ])
                    }
                  >
                    Add a person
                  </GhostButton>
                  {splits.length > 0 && (
                    <Muted>
                      Your reported spend is the amount minus their shares.
                    </Muted>
                  )}
                </Stack>
              </Field>
            )}

            <Field>
              <FieldLabel htmlFor="date">Date</FieldLabel>
              <Input id="date" type="date" {...register("date")} />
            </Field>

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save"}
            </Button>

            {submitError && <ErrorText>{submitError}</ErrorText>}
            {lastSaved && (
              <Saved>
                <CheckCircle size={16} weight="fill" />
                Saved {lastSaved}
              </Saved>
            )}
            {accountsForCurrency.length === 0 && (
              <Muted>
                No active {currency} account yet — add one in Settings.
              </Muted>
            )}
          </Stack>
        </form>
      </Card>
    </Screen>
  );
}
