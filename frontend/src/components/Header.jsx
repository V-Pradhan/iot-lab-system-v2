import { NavLink } from 'react-router-dom';
import { LAB_SUB, LAB_TITLE } from '../contact';

const ROLE = { admin: 'Administrator', teacher: 'Teacher', lab_assistant: 'Lab assistant' };

/** Top bar: lab name on the left, signed-in user in the middle, university logo on the right. */
export default function Header({ user, onLogout }) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="logo-tile" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="6" y="6" width="12" height="12" rx="2" /><rect x="9.5" y="9.5" width="5" height="5" rx="1" />
            <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
          </svg>
        </span>
        <div><h2>{LAB_TITLE}</h2><small>{LAB_SUB}</small></div>
      </div>

      <div className="user-pill">
        <NavLink to="/account" className="user-link" title="My account">
          <span className="avatar" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="8" r="4.2" /><path d="M3.5 21c0-4.7 3.8-7.5 8.5-7.5s8.5 2.8 8.5 7.5z" /></svg>
          </span>
          <span className="who-text"><strong>{user.full_name}</strong><span>{ROLE[user.role]}</span></span>
        </NavLink>
        <button className="logout" onClick={onLogout} aria-label="Sign out" title="Sign out">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" /><path d="M16 8l4 4-4 4M20 12H9" />
          </svg>
        </button>
      </div>

      <img className="cu-logo" src="/cu-logo.png" alt="Chandigarh University" />
    </header>
  );
}
