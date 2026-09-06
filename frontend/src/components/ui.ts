import styled from "styled-components";

import type { Theme } from "../theme";

type SpaceKey = keyof Theme["space"];

export const Card = styled.div`
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => theme.space.xl};
  box-shadow: ${({ theme }) => theme.shadow.sm};

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const Button = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 2.75rem;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  background: ${({ theme }) => theme.color.primary};
  color: ${({ theme }) => theme.color.primaryText};
  border: none;
  border-radius: ${({ theme }) => theme.radius.md};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  cursor: pointer;
  transition: background ${({ theme }) => theme.transition.fast};

  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.color.primaryHover};
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`;

export const Input = styled.input`
  width: 100%;
  min-height: 2.75rem;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  background: ${({ theme }) => theme.color.bg};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.text};

  &::placeholder {
    color: ${({ theme }) => theme.color.textFaint};
  }
`;

export const FieldLabel = styled.label`
  display: block;
  margin-bottom: ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const ErrorText = styled.p`
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.sm};
  margin-top: ${({ theme }) => theme.space.sm};
`;

export const PageTitle = styled.h1`
  font-size: ${({ theme }) => theme.fontSize.xl};
  margin-bottom: ${({ theme }) => theme.space.lg};

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    font-size: ${({ theme }) => theme.fontSize.lg};
    margin-bottom: ${({ theme }) => theme.space.md};
  }
`;

export const Muted = styled.p`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Select = styled.select`
  width: 100%;
  min-height: 2.75rem;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  background: ${({ theme }) => theme.color.bg};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.text};
  max-width: 100%;
`;

export const GhostButton = styled(Button)`
  background: transparent;
  color: ${({ theme }) => theme.color.textMuted};
  border: 1px solid ${({ theme }) => theme.color.border};

  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.color.surfaceRaised};
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Stack = styled.div<{ $gap?: SpaceKey }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme, $gap }) => theme.space[$gap ?? "lg"]};
  min-width: 0;
`;

export const Row = styled.div<{ $gap?: SpaceKey }>`
  display: flex;
  align-items: center;
  gap: ${({ theme, $gap }) => theme.space[$gap ?? "md"]};
  flex-wrap: wrap;
  min-width: 0;
`;

export const Field = styled.div`
  display: flex;
  flex-direction: column;
  min-width: 0;
`;

/** A responsive form/stat grid: auto-fit columns on desktop, a single
 *  column below the small breakpoint. Render as a <form> with `as="form"`. */
export const FormGrid = styled.div<{ $min?: string }>`
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(${({ $min }) => $min ?? "10rem"}, 1fr)
  );
  gap: ${({ theme }) => theme.space.md};
  align-items: end;

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    grid-template-columns: 1fr;
  }
`;

export const Badge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.sm}`};
  border-radius: ${({ theme }) => theme.radius.pill};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  background: ${({ theme }) => theme.color.surfaceRaised};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Th = styled.th<{ $align?: "left" | "right" | "center" }>`
  text-align: ${({ $align }) => $align ?? "left"};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  white-space: nowrap;

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  }
`;

export const Td = styled.td<{ $align?: "left" | "right" | "center" }>`
  text-align: ${({ $align }) => $align ?? "left"};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  overflow-wrap: break-word;

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  }
`;

export const TableScroll = styled.div`
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
`;
