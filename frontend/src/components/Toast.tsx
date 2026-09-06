import { CheckCircle, Info, WarningCircle, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import styled, { keyframes } from "styled-components";

export type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

// A module-level bus so non-React code (the query client) can raise toasts too.
type Listener = (t: { kind: ToastKind; text: string }) => void;
const listeners = new Set<Listener>();
const recent = new Map<string, number>();

/** Raise a toast from anywhere. Identical messages within 4s are collapsed. */
export function pushToast(kind: ToastKind, text: string): void {
  const key = `${kind}:${text}`;
  const now = Date.now();
  if (now - (recent.get(key) ?? 0) < 4000) return;
  recent.set(key, now);
  listeners.forEach((l) => l({ kind, text }));
}

const slideIn = keyframes`
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
`;

const Stack = styled.div`
  position: fixed;
  top: ${({ theme }) => theme.space.lg};
  right: ${({ theme }) => theme.space.lg};
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  pointer-events: none;

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    left: ${({ theme }) => theme.space.md};
    right: ${({ theme }) => theme.space.md};
    top: ${({ theme }) => theme.space.md};
  }
`;

const Item = styled.div<{ $kind: ToastKind }>`
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};
  min-width: 15rem;
  max-width: 22.5rem;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  background: ${({ theme }) => theme.color.surfaceRaised};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-left: 3px solid
    ${({ theme, $kind }) =>
      $kind === "success"
        ? theme.color.success
        : $kind === "error"
          ? theme.color.danger
          : theme.color.primary};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: ${({ theme }) => theme.shadow.md};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.sm};
  animation: ${slideIn} ${({ theme }) => theme.transition.base};

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    max-width: none;
  }
`;

const IconSlot = styled.span<{ $kind: ToastKind }>`
  flex-shrink: 0;
  display: flex;
  margin-top: 1px;
  color: ${({ theme, $kind }) =>
    $kind === "success"
      ? theme.color.success
      : $kind === "error"
        ? theme.color.danger
        : theme.color.primary};
`;

const Text = styled.span`
  flex: 1;
  line-height: ${({ theme }) => theme.lineHeight.normal};
  word-break: break-word;
`;

const Close = styled.button`
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: ${({ theme }) => theme.color.textFaint};
  display: flex;

  &:hover {
    color: ${({ theme }) => theme.color.text};
  }
`;

const ICONS = { success: CheckCircle, error: WarningCircle, info: Info };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener: Listener = ({ kind, text }) => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, kind, text }].slice(-4));
      window.setTimeout(
        () => setToasts((current) => current.filter((t) => t.id !== id)),
        4200,
      );
    };
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const dismiss = (id: number) =>
    setToasts((current) => current.filter((t) => t.id !== id));

  return (
    <>
      {children}
      <Stack aria-live="polite">
        {toasts.map((t) => {
          const Icon = ICONS[t.kind];
          return (
            <Item key={t.id} $kind={t.kind} role="status">
              <IconSlot $kind={t.kind}>
                <Icon size={18} weight="fill" />
              </IconSlot>
              <Text>{t.text}</Text>
              <Close
                type="button"
                aria-label="Dismiss"
                onClick={() => dismiss(t.id)}
              >
                <X size={14} />
              </Close>
            </Item>
          );
        })}
      </Stack>
    </>
  );
}

/** Toast helpers for use inside components. */
export function useToast() {
  return useMemo(
    () => ({
      success: (text: string) => pushToast("success", text),
      error: (text: string) => pushToast("error", text),
      info: (text: string) => pushToast("info", text),
    }),
    [],
  );
}
