import { SignOut } from "@phosphor-icons/react";
import { NavLink, Outlet } from "react-router-dom";
import styled from "styled-components";

import { useAuth } from "../auth/AuthContext";
import { useMeta } from "../lib/meta";
import { navItems } from "./nav";

const Layout = styled.div`
  display: grid;
  grid-template-columns: ${({ theme }) => theme.layout.sidebarWidth} 1fr;
  min-height: 100%;

  @media (max-width: ${({ theme }) => theme.bp.md}) {
    grid-template-columns: 1fr;
  }
`;

/* ---------------------------------------------------------------- desktop */

const Sidebar = styled.aside`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border-right: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: ${({ theme }) => theme.bp.md}) {
    display: none;
  }
`;

const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-weight: ${({ theme }) => theme.fontWeight.bold};
  font-size: ${({ theme }) => theme.fontSize.lg};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  margin-bottom: ${({ theme }) => theme.space.md};
`;

const DemoBadge = styled.span`
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.sm}`};
  border-radius: ${({ theme }) => theme.radius.pill};
  background: ${({ theme }) => theme.color.warning};
  color: ${({ theme }) => theme.color.bg};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  text-transform: uppercase;
  letter-spacing: 0.04em;
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

/* ----------------------------------------------------------------- mobile */

const TopBar = styled.header`
  display: none;

  @media (max-width: ${({ theme }) => theme.bp.md}) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: ${({ theme }) => theme.space.sm};
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
    background: ${({ theme }) => theme.color.surface};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    position: sticky;
    top: 0;
    z-index: 20;
  }
`;

const TopBrand = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-weight: ${({ theme }) => theme.fontWeight.bold};
`;

const IconButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  background: none;
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  &:active {
    background: ${({ theme }) => theme.color.surfaceRaised};
  }
`;

const BottomNav = styled.nav`
  display: none;

  @media (max-width: ${({ theme }) => theme.bp.md}) {
    display: flex;
    position: fixed;
    inset: auto 0 0 0;
    z-index: 20;
    min-height: ${({ theme }) => theme.layout.bottomNavHeight};
    background: ${({ theme }) => theme.color.surface};
    border-top: 1px solid ${({ theme }) => theme.color.border};
    padding-bottom: env(safe-area-inset-bottom);
    overflow-x: auto;
    scrollbar-width: none;
    scroll-snap-type: x proximity;

    &::-webkit-scrollbar {
      display: none;
    }
  }
`;

const BottomLink = styled(NavLink)`
  flex: 1 0 auto;
  min-width: 4.25rem;
  scroll-snap-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.xs}`};
  color: ${({ theme }) => theme.color.textFaint};
  font-size: 0.625rem;
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  white-space: nowrap;

  svg {
    transition: transform ${({ theme }) => theme.transition.fast};
  }

  &.active {
    color: ${({ theme }) => theme.color.primary};
  }

  &.active svg {
    transform: translateY(-1px) scale(1.08);
  }
`;

const Content = styled.div`
  min-width: 0;
`;

const Main = styled.main`
  padding: ${({ theme }) => theme.space.xxl};
  width: 100%;
  max-width: ${({ theme }) => theme.layout.contentMaxWidth};
  margin: 0 auto;
  min-width: 0;

  @media (max-width: ${({ theme }) => theme.bp.md}) {
    padding: ${({ theme }) => theme.space.lg};
    padding-bottom: calc(
      ${({ theme }) => theme.layout.bottomNavHeight} +
        env(safe-area-inset-bottom) + ${({ theme }) => theme.space.lg}
    );
  }
`;

export function AppShell() {
  const { logout } = useAuth();
  const meta = useMeta();
  const items = navItems.filter(
    (item) => !item.requiresImport || meta.import_enabled,
  );

  return (
    <Layout>
      <Sidebar>
        <Brand>
          safe-to-spend
          {meta.demo_mode && <DemoBadge>Demo</DemoBadge>}
        </Brand>
        {items.map(({ to, label, icon: Icon, end }) => (
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

      <Content>
        <TopBar>
          <TopBrand>
            safe-to-spend
            {meta.demo_mode && <DemoBadge>Demo</DemoBadge>}
          </TopBrand>
          <IconButton
            type="button"
            onClick={logout}
            aria-label="Sign out"
          >
            <SignOut size={20} />
          </IconButton>
        </TopBar>

        <Main>
          <Outlet />
        </Main>
      </Content>

      <BottomNav>
        {items.map(({ to, label, icon: Icon, end }) => (
          <BottomLink key={to} to={to} end={end}>
            <Icon size={22} />
            {label}
          </BottomLink>
        ))}
      </BottomNav>
    </Layout>
  );
}
