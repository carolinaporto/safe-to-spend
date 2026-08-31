import styled from "styled-components";

import { Card, Muted, PageTitle } from "../components/ui";

const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <Wrap>
      <PageTitle>{title}</PageTitle>
      <Card>
        <Muted>Arrives in {phase}.</Muted>
      </Card>
    </Wrap>
  );
}

export const Transfers = () => <Placeholder title="Transfers" phase="Phase 4" />;
export const People = () => <Placeholder title="People" phase="Phase 4" />;
export const Income = () => <Placeholder title="Income" phase="Phase 4" />;
