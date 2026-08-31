import { useState, type FormEvent } from "react";
import styled from "styled-components";

import { useAuth } from "../auth/AuthContext";
import { Button, Card, ErrorText, FieldLabel, Input } from "../components/ui";
import { ApiError } from "../lib/api";

const Screen = styled.div`
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: ${({ theme }) => theme.space.xl};
`;

const Box = styled(Card)`
  width: 100%;
  max-width: 360px;
`;

const Heading = styled.h1`
  font-size: ${({ theme }) => theme.fontSize.lg};
  margin-bottom: ${({ theme }) => theme.space.xs};
`;

const Sub = styled.p`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  margin-bottom: ${({ theme }) => theme.space.xl};
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export function Login() {
  const { login } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reach the server",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Box>
        <Heading>safe-to-spend</Heading>
        <Sub>Enter your password to continue.</Sub>
        <Form onSubmit={onSubmit}>
          <div>
            <FieldLabel htmlFor="password">Password</FieldLabel>
            <Input
              id="password"
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={busy || !password}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
          {error && <ErrorText>{error}</ErrorText>}
        </Form>
      </Box>
    </Screen>
  );
}
