// Small shared inline-SVG icon set (stroke icons that inherit currentColor).
const base = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8 };

export const GridIcon = () => (
  <svg {...base}>
    <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.5" />
    <rect x="13" y="3.5" width="7.5" height="7.5" rx="1.5" />
    <rect x="3.5" y="13" width="7.5" height="7.5" rx="1.5" />
    <rect x="13" y="13" width="7.5" height="7.5" rx="1.5" />
  </svg>
);

export const BookIcon = () => (
  <svg {...base}>
    <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5v-15Z" strokeLinejoin="round" />
    <path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3" strokeLinejoin="round" />
    <path d="M9 7.5h6M9 11h4" strokeLinecap="round" />
  </svg>
);

export const InfoIcon = () => (
  <svg {...base}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5" strokeLinecap="round" />
    <path d="M12 7.75h.01" strokeLinecap="round" />
  </svg>
);

export const MenuIcon = () => (
  <svg {...base}>
    <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
  </svg>
);

export const PanelToggleIcon = () => (
  <svg {...base}>
    <rect x="3.25" y="4.5" width="17.5" height="15" rx="3.5" />
    <path d="M9.5 4.5v15" />
    <path d="M7 10.25 5.25 12 7 13.75" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ChevronDownIcon = () => (
  <svg {...base} strokeWidth="2">
    <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const CheckIcon = () => (
  <svg {...base} strokeWidth="2.2">
    <path d="m5 13 4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const SearchIcon = () => (
  <svg {...base}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.3-4.3" strokeLinecap="round" />
  </svg>
);

export const DownloadIcon = () => (
  <svg {...base}>
    <path d="M12 4v11M12 15l-4-4M12 15l4-4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const AlertIcon = () => (
  <svg {...base}>
    <path d="M12 3.5 21.5 20h-19L12 3.5Z" strokeLinejoin="round" />
    <path d="M12 10v4.5M12 17.5h.01" strokeLinecap="round" />
  </svg>
);

export const FlameIcon = () => (
  <svg {...base}>
    <path d="M12 3c.5 3-1.5 4.5-3 6.5-1.3 1.8-2 3.3-2 5a5 5 0 0 0 10 0c0-1.8-.8-3.2-2-4.5-.3 1.2-1 2-2 2.3.6-2.700.3-6.300-1-9.300Z" strokeLinejoin="round" />
  </svg>
);

export const TrendIcon = () => (
  <svg {...base}>
    <path d="M3.5 17 9 11.5l4 4L20.5 8" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M15 8h5.500v5.500" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ThermometerIcon = () => (
  <svg {...base}>
    <path d="M10 14.500V5a2 2 0 1 1 4 0v9.500a4 4 0 1 1-4 0Z" strokeLinejoin="round" />
    <path d="M12 9v7" strokeLinecap="round" />
  </svg>
);

export const SigmaIcon = () => (
  <svg {...base}>
    <path d="M18 5.500H6.500l6 6.500-6 6.500H18" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const PinIcon = () => (
  <svg {...base}>
    <path d="M12 21s6.500-5.700 6.500-11a6.500 6.500 0 1 0-13 0c0 5.300 6.500 11 6.500 11Z" strokeLinejoin="round" />
    <circle cx="12" cy="10" r="2.300" />
  </svg>
);
