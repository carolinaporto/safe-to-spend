import { SignOut } from "@phosphor-icons/react";
import { NavLink, Outlet } from "react-router-dom";
import styled from "styled-components";

import { useAuth } from "../auth/AuthContext";
import { navItems } from "./nav";

const Layout = styled.div`
  display: grid;
  grid-template-columns: ${({ theme }) => theme.layout.sidebarWidth} 1fr;
  min-height: 100%;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const Sidebar = styled.aside`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border-right: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 720px) {
    flex-direction: row;
    flex-wrap: wrap;
    border-right: none;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }
`;

const Brand = styled.div`
  font-weight: ${({ theme }) => theme.fontWeight.bold};
  font-size: ${({ theme }) => theme.fontSize.lg};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  margin-bottom: ${({ theme }) => theme.space.md};

  @media (max-width: 720px) {
    margin-bottom: 0;
  }
`;

const NavItemLink = styled(NavLink)`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  transition: background ${({ theme }) => theme.transition.fast},
    color ${({ theme }) => theme.transition.fast};

  &:hover {
    background: ${({ theme }) => theme.color.surfaceRaised};
    color: ${({ theme }) => theme.color.text};
  }

  &.active {
    background: ${({ theme }) => theme.color.surfaceRaised};
    color: ${({ theme }) => theme.color.text};
  }
`;

const Spacer = styled.div`
  flex: 1;

  @media (max-width: 720px) {
    display: none;
  }
`;

const SignOutButton = styled.button`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border: none;
  background: none;
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surfaceRaised};
    color: ${({ theme }) => theme.color.text};
  }
`;

const Main = styled.main`
  padding: ${({ theme }) => theme.space.xxl};
  width: 100%;
  max-width: ${({ theme }) => theme.layout.contentMaxWidth};
  margin: 0 auto;

  @media (max-width: 720px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export function AppShell() {
  const { logout } = useAuth();

  return (
    <Layout>
      <Sidebar>
        <Brand>safe-to-spend</Brand>
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavItemLink key={to} to={to} end={end}>
            <Icon size={18} />
            {label}
          </NavItemLink>
        ))}
        <Spacer />
        <SignOutButton type="button" onClick={logout}>
          <SignOut size={18} />
          Sign out
        </SignOutButton>
      </Sidebar>
      <Main>
        <Outlet />
      </Main>
    </Layout>
  );
}
