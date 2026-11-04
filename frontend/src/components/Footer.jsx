import { NavLink } from 'react-router-dom';
import { CONTACT, LAB_SUB, LAB_TITLE, UNIVERSITY } from '../contact';

const icon = (path) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{path}</svg>
);
const PERSON = icon(<><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" /></>);
const PHONE = icon(<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />);
const PIN = icon(<><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></>);
const MAIL = icon(<><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></>);

const LINKS = [['/issue', 'Issue equipment'], ['/loans', 'Loans and returns'], ['/registrations', 'Registrations'],
  ['/students', 'Students'], ['/inventory', 'Inventory'], ['/reports', 'Reports']];

/** Red footer with the lab description, quick links (inside the app) and the contact details. */
export default function Footer({ showLinks = false }) {
  return (
    <footer className="footer">
      <div className="footer-grid">
        <div>
          <h3>{LAB_TITLE}</h3>
          <p>Equipment issue, return and student registration for the {LAB_TITLE.replace(' Lab', '')} laboratory of the {LAB_SUB}, {UNIVERSITY}.</p>
        </div>
        {showLinks && (
          <div>
            <h3>Quick Links</h3>
            <ul>{LINKS.map(([to, label]) => <li key={to}><NavLink to={to}>{label}</NavLink></li>)}</ul>
          </div>
        )}
        <div>
          <h3>Contact Us</h3>
          <ul className="contact">
            <li>{PERSON}<span>{CONTACT.name}, {CONTACT.title}</span></li>
            <li>{PHONE}<a href={`tel:${CONTACT.phoneLink}`}>{CONTACT.phone}</a></li>
            <li>{PIN}<span>{CONTACT.address}</span></li>
            <li>{MAIL}<a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a></li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; 2026 {UNIVERSITY} - {LAB_SUB}. All Rights Reserved.</p>
      </div>
    </footer>
  );
}
