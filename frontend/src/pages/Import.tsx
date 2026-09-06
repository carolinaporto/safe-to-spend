import { CheckCircle, UploadSimple, Warning } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import styled from "styled-components";

import {
  Badge,
  Button,
  Card,
  ErrorText,
  Field,
  FieldLabel,
  GhostButton,
  Muted,
  PageTitle,
  Row,
  Select,
  Stack,
  Table,
  TableScroll,
  Td,
  Th,
} from "../components/ui";
import { ReviewQueue } from "../components/ReviewQueue";
import { ApiError } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import {
  useAccounts,
  useCategories,
  useImportCommit,
  useImportPreview,
} from "../lib/queries";
import type { ImportRowStatus, PreviewRow } from "../lib/types";
import type { Theme } from "../theme";

const PARSERS = ["auto", "chase", "amex", "wise", "generic"];

const STATUS_TOKEN: Record<ImportRowStatus, keyof Theme["color"]> = {
  new: "success",
  duplicate: "textFaint",
  uncategorized: "warning",
};

const Controls = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
  gap: ${({ theme }) => theme.space.md};
  align-items: end;
`;

const FileInput = styled.input`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

const StatusBadge = styled(Badge)<{ $status: ImportRowStatus }>`
  color: ${({ theme, $status }) => theme.color[STATUS_TOKEN[$status]]};
  text-transform: capitalize;
`;

const SummaryRow = styled(Row)`
  gap: ${({ theme }) => theme.space.lg};
`;

const RowCategory = styled(Select)`
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.xs}`};
  font-size: ${({ theme }) => theme.fontSize.xs};
  max-width: 10rem;
`;

const Done = styled(Card)`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  color: ${({ theme }) => theme.color.success};
`;

export function Import() {
  const accounts = useAccounts();
  const categories = useCategories();
  const preview = useImportPreview();
  const commit = useImportCommit();

  const [accountId, setAccountId] = useState<number | "">("");
  const [parser, setParser] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  const [overrides, setOverrides] = useState<Record<string, number | null>>({});
  const [skip, setSkip] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const rows = preview.data?.rows ?? [];
  const activeCategories = (categories.data ?? []).filter((c) => !c.is_archived);

  const importable = useMemo(
    () =>
      rows.filter((r) => r.status !== "duplicate" && !skip.has(r.key)).length,
    [rows, skip],
  );

  function reset() {
    preview.reset();
    setOverrides({});
    setSkip(new Set());
    setResult(null);
  }

  async function runPreview() {
    setError(null);
    setResult(null);
    if (!accountId || !file) return;
    try {
      await preview.mutateAsync({
        accountId,
        parser: parser === "auto" ? "" : parser,
        file,
      });
      setOverrides({});
      setSkip(new Set());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not read the file");
    }
  }

  async function runCommit() {
    setError(null);
    if (!accountId || !file) return;
    try {
      const res = await commit.mutateAsync({
        accountId,
        parser: parser === "auto" ? "" : parser,
        file,
        overrides,
        skip: [...skip],
      });
      setResult(
        `Imported ${res.imported_count}, skipped ${res.duplicate_count} duplicate${
          res.duplicate_count === 1 ? "" : "s"
        }.`,
      );
      reset();
      setFile(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    }
  }

  function categoryFor(r: PreviewRow): number | "" {
    const o = overrides[r.key];
    if (o !== undefined) return o ?? "";
    return r.category_id ?? "";
  }

  return (
    <Stack $gap="lg">
      <PageTitle>Import statements</PageTitle>

      <Card>
        <Controls>
          <Field>
            <FieldLabel>Account</FieldLabel>
            <Select
              value={accountId}
              onChange={(e) =>
                setAccountId(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Select…</option>
              {(accounts.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.currency})
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Format</FieldLabel>
            <Select value={parser} onChange={(e) => setParser(e.target.value)}>
              {PARSERS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>CSV file</FieldLabel>
            <FileInput
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                reset();
              }}
            />
          </Field>
          <Button
            type="button"
            disabled={!accountId || !file || preview.isPending}
            onClick={runPreview}
          >
            <UploadSimple size={16} />
            {preview.isPending ? "Reading…" : "Preview"}
          </Button>
        </Controls>
      </Card>

      {result && (
        <Done>
          <CheckCircle size={18} weight="fill" />
          {result}
        </Done>
      )}
      {error && <ErrorText>{error}</ErrorText>}

      {preview.data && (
        <>
          <SummaryRow>
            <Muted as="span">
              Parsed as <strong>{preview.data.parser}</strong> ·{" "}
              {preview.data.summary.total} rows
            </Muted>
            <Badge>{preview.data.summary.new} new</Badge>
            <Badge>{preview.data.summary.uncategorized} uncategorized</Badge>
            <Badge>{preview.data.summary.duplicate} duplicate</Badge>
          </SummaryRow>

          <TableScroll>
            <Table>
              <thead>
                <tr>
                  <Th>Import</Th>
                  <Th>Status</Th>
                  <Th>Date</Th>
                  <Th>Merchant</Th>
                  <Th>Category</Th>
                  <Th $align="right">Amount</Th>
                  <Th $align="right">USD</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const isDup = r.status === "duplicate";
                  return (
                    <tr key={r.key}>
                      <Td>
                        <input
                          type="checkbox"
                          aria-label={`Import ${r.merchant_raw}`}
                          disabled={isDup}
                          checked={!isDup && !skip.has(r.key)}
                          onChange={(e) =>
                            setSkip((s) => {
                              const next = new Set(s);
                              e.target.checked
                                ? next.delete(r.key)
                                : next.add(r.key);
                              return next;
                            })
                          }
                        />
                      </Td>
                      <Td>
                        <StatusBadge $status={r.status}>
                          {r.status === "uncategorized" && (
                            <Warning size={12} weight="fill" />
                          )}
                          {r.status}
                        </StatusBadge>
                      </Td>
                      <Td>{formatDate(r.date)}</Td>
                      <Td>
                        {r.merchant_clean || r.merchant_raw || "—"}
                        {r.merchant_clean && (
                          <Muted as="span"> · {r.merchant_raw}</Muted>
                        )}
                      </Td>
                      <Td>
                        <RowCategory
                          value={categoryFor(r)}
                          disabled={isDup}
                          onChange={(e) =>
                            setOverrides((o) => ({
                              ...o,
                              [r.key]: e.target.value
                                ? Number(e.target.value)
                                : null,
                            }))
                          }
                        >
                          <option value="">Uncategorized</option>
                          {activeCategories.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </RowCategory>
                      </Td>
                      <Td $align="right">
                        {r.direction === "in" ? "+" : "−"}
                        {formatMoney(r.amount, r.currency)}
                      </Td>
                      <Td $align="right">
                        {formatMoney(r.amount_usd, "USD")}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </TableScroll>

          <Row>
            <Button
              type="button"
              disabled={importable === 0 || commit.isPending}
              onClick={runCommit}
            >
              {commit.isPending
                ? "Importing…"
                : `Import ${importable} row${importable === 1 ? "" : "s"}`}
            </Button>
            <GhostButton type="button" onClick={reset}>
              Discard
            </GhostButton>
          </Row>
        </>
      )}

      <ReviewQueue />
    </Stack>
  );
}
