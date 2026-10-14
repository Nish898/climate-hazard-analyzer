import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { BookIcon, GridIcon, InfoIcon, MenuIcon, PanelToggleIcon } from "../components/icons.jsx";

const NAV_SECTIONS = [
  { title: "Workspace", items: [{ to: "/", end: true, label: "Analyzer", Icon: GridIcon }] },
  {
    title: "Learn",
    items: [
      { to: "/method", label: "Method", Icon: BookIcon },
      { to: "/about", label: "About", Icon: InfoIcon },
    ],
  },
];
const TITLES = Object.fromEntries(NAV_SECTIONS.flatMap((s) => s.items).map((i) => [i.to, i.label]));
const COLLAPSED_KEY = "sidebar_collapsed";

function BrandMark() {
  return (
    <svg className="brand-icon" viewBox="0 0 40 40" aria-hidden="true">
      <defs>
        <linearGradient id="brand-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#e35336" />
          <stop offset="1" stopColor="#a0522d" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="url(#brand-grad)" />
      <circle cx="20" cy="17" r="5.5" fill="#fff9f2" />
      <g stroke="#fff9f2" strokeWidth="2" strokeLinecap="round">
        <path d="M20 6.500v2.500M9.500 17H12M28 17h2.500M12.600 9.600l1.800 1.800M27.600 9.600l-1.800 1.800" />
      </g>
      <path d="M8 29c3-3 5-3 8 0s5 3 8 0 5-3 8 0" fill="none" stroke="#fff9f2" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function AppLayout() {
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  const toggleCollapsed = () =>
    setCollapsed((prev) => {
      try {
        localStorage.setItem(COLLAPSED_KEY, String(!prev));
      } catch {
        // storage unavailable: the choice just will not persist
      }
      return !prev;
    });

  // The mobile drawer must never stay open across a navigation.
  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <div className="app-layout">
      {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}

      <aside className={"sidebar" + (collapsed ? " sidebar--collapsed" : "") + (mobileOpen ? " sidebar--mobile-open" : "")}>
        <div className="sidebar-brand">
          {collapsed ? (
            <button type="button" className="sidebar-brand-icon-btn" onClick={toggleCollapsed} aria-label="Expand sidebar" title="Expand sidebar">
              <BrandMark />
            </button>
          ) : (
            <>
              <BrandMark />
              <span className="sidebar-brand-text">
                Hazard Analyzer
                <small>Climate trends</small>
              </span>
              <button type="button" className="sidebar-collapse-toggle" onClick={toggleCollapsed} aria-label="Collapse sidebar" title="Collapse sidebar">
                <PanelToggleIcon />
              </button>
            </>
          )}
        </div>

        <nav className="sidebar-nav">
          {NAV_SECTIONS.map((section) => (
            <div className="sidebar-section" key={section.title}>
              <span className="sidebar-section-label">{section.title}</span>
              {section.items.map(({ to, end, label, Icon }) => (
                <NavLink key={to} to={to} end={end} title={label}>
                  <span className="sidebar-icon">
                    <Icon />
                  </span>
                  <span className="sidebar-label">{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">Data: ERA5 reanalysis via Open-Meteo. Heatwave hazard.</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button type="button" className="sidebar-menu-toggle" onClick={() => setMobileOpen(true)} aria-label="Open menu" title="Open menu">
            <MenuIcon />
          </button>
          <div className="topbar-title">
            <h1>{TITLES[pathname] || "Hazard Analyzer"}</h1>
          </div>
          <div className="topbar-right">
            <Link to="/about" className="topbar-icon-btn" aria-label="About" title="About">
              <InfoIcon />
            </Link>
          </div>
        </header>

        <section className="page-content">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
