import { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { Modal, useToast } from '../ui';

/** QR code (and link) that opens the student self-registration form for one lab. */
export default function QrModal({ lab, onClose }) {
  const toast = useToast();
  const url = `${window.location.origin}/#/register/${lab.code}`;
  const [img, setImg] = useState('');
  useEffect(() => { QRCode.toDataURL(url, { width: 420, margin: 2 }).then(setImg); }, [url]);
  const local = /localhost|127\.0\.0\.1|192\.168\./.test(window.location.hostname);

  return (
    <Modal title={`Student registration QR: ${lab.name}`} onClose={onClose}>
      <div className="qr-box">
        {img && <img src={img} alt={`QR code to register for ${lab.name}`} />}
        <p className="muted small">The student scans this with the phone camera, fills the form, and the request appears on the Registrations page. You can print it for the lab door or counter.</p>
        {local && <p className="notice small">This address works only on this network. Open the site from its live address so students outside can use the QR code.</p>}
        <p><code className="break">{url}</code></p>
        <div className="actions">
          <button className="btn ghost" onClick={() => navigator.clipboard?.writeText(url).then(() => toast('Link copied'))}>Copy link</button>
          <button className="btn" onClick={() => window.print()}>Print</button>
        </div>
      </div>
    </Modal>
  );
}
