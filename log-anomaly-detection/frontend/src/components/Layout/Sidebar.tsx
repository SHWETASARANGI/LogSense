import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: DashboardIcon },
  { to: "/anomalies", label: "Anomalies", icon: AnomalyIcon },
  { to: "/logs", label: "Logs", icon: LogsIcon },
  { to: "/model", label: "Model", icon: ModelIcon },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-none flex-col border-r border-hairline bg-panel">
      <div className="flex items-center gap-2 px-5 py-6">
        <span className="h-2 w-2 rounded-full bg-signal shadow-glow" />
        <span className="font-display text-lg font-semibold tracking-tight text-text-primary">
          LogSense
        </span>
      </div>

      <nav className="flex flex-col gap-1 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-panel-raised text-signal"
                  : "text-text-muted hover:bg-panel-raised hover:text-text-primary"
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto px-5 py-4 font-mono text-[11px] text-text-muted">
        unsupervised anomaly detection
      </div>
    </aside>
  );
}

function DashboardIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1.5" y="1.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="8.5" y="1.5" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="8.5" y="7.5" width="6" height="7" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="1.5" y="9.5" width="6" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function AnomalyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path
        d="M1.5 8h2.5l1.5-4.5 2 9 1.5-6 1 1.5h4.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LogsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M2 3.5h12M2 8h12M2 12.5h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function ModelIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.4 3.6l-1.4 1.4M4.9 11l-1.4 1.4M12.4 12.4l-1.4-1.4M4.9 5l-1.4-1.4"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
