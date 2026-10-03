import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearSession, currentUser } from "./api";
import Login from "./pages/Login.jsx";
import Requests from "./pages/Requests.jsx";
import RequestDetail from "./pages/RequestDetail.jsx";
import NewRequest from "./pages/NewRequest.jsx";
import ImportPage from "./pages/ImportPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import ChangePassword from "./pages/ChangePassword.jsx";
import { BarChart3, FilePlus2, Inbox, LogOut, Upload, Users } from "lucide-react";

function Guard({ roles, children }) {
  const user = currentUser();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState(currentUser());

  useEffect(() => {
    setUser(currentUser());
  }, []);

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={() => setUser(currentUser())} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  if (user.must_change_password) {
    return <ChangePassword user={user} onComplete={setUser} onLogout={() => setUser(null)} />;
  }

  const isStaff = user.role === "operator" || user.role === "admin";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <img className="brand-logo" src="/neotix-datadesk-logo.png" alt="Neotix Data Desk" />
        </div>
        <nav className="nav">
          <span className="nav-label">Workspace</span>
          <NavLink to="/" end><Inbox size={15} /> Requests</NavLink>
          {user.role === "client" && <NavLink to="/new"><FilePlus2 size={15} /> New request</NavLink>}
          {isStaff && <NavLink to="/import"><Upload size={15} /> Import</NavLink>}
          {isStaff && <NavLink to="/analytics"><BarChart3 size={15} /> Analytics</NavLink>}
          {user.role === "admin" && <NavLink to="/users"><Users size={15} /> Users</NavLink>}
        </nav>
        <div className="sidebar-footer">
          <div className="profile">
            <div className="avatar">{user.name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div>
            <div className="profile-copy">
              <b>{user.name}</b>
              <span className={`role-badge role-${user.role}`}>{user.role}</span>
            </div>
          </div>
          <button
            className="icon-button"
            title="Log out"
            onClick={() => {
              clearSession();
              setUser(null);
              navigate("/login");
            }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <main className="page">
        <Routes>
          <Route path="/" element={<Guard><Requests user={user} /></Guard>} />
          <Route path="/requests/:id" element={<Guard><RequestDetail user={user} /></Guard>} />
          <Route path="/new" element={<Guard roles={["client"]}><NewRequest /></Guard>} />
          <Route path="/import" element={<Guard roles={["operator", "admin"]}><ImportPage /></Guard>} />
          <Route path="/analytics" element={<Guard roles={["operator", "admin"]}><AnalyticsPage /></Guard>} />
          <Route path="/users" element={<Guard roles={["admin"]}><UsersPage /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
