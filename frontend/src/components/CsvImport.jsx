import { useEffect, useState } from 'react';
import { api } from '../api';
import { Badge, Modal, useToast } from '../ui';

const TEMPLATE = 'name,category,total,damaged,missing,maintenance,notes\nArduino Uno R3,Microcontroller,20,0,0,0,\nBreadboard,Prototyping,40,2,0,0,Half size\n';
const ACTION = { add: ['green', 'New'], update: ['blue', 'Update'], unchanged: ['gray', 'No change'], skip: ['gray', 'Skipped'] };

/** Add or update many items from a CSV file. The file is checked first; nothing is saved if a row has an error. */
export default function CsvImport({ onClose, onDone }) {
  const toast = useToast();
  const [text, setText] = useState('');
  const [filename, setFilename] = useState('');
  const [mode, setMode] = useState('add_update');
  const [res, setRes] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const check = async (csv, m, name) => {
    setError(''); setRes(null);
    try { setRes(await api.post('/inventory/import', { csv, mode: m, dry_run: true, filename: name })); }
    catch (e) { setError(e.message); }
  };
  useEffect(() => { if (text) check(text, mode, filename); }, [mode]); // eslint-disable-line

  const pick = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const content = await file.text();
    setText(content); setFilename(file.name);
    check(content, mode, file.name);
  };

  const save = async () => {
    setBusy(true);
    try {
      const r = await api.post('/inventory/import', { csv: text, mode, dry_run: false, filename });
      toast(`Imported: ${r.created} new, ${r.updated} updated`);
      onDone();
    } catch (e) { setError(e.message); setBusy(false); }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([TEMPLATE], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url; a.download = 'inventory-template.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const ready = res && res.error_count === 0 && res.created + res.updated > 0;

  return (
    <Modal title="Import inventory from CSV" onClose={onClose} wide>
      <div className="form">
        <p className="muted small">
          Use a CSV file (in Excel: Save As, CSV). The first row must be a header with <strong>name</strong> and <strong>total</strong>; optional columns are
          category, damaged, missing, maintenance and notes. <button type="button" className="link" onClick={download}>Download an example file</button>
        </p>
        <div className="csv-row">
          <input type="file" accept=".csv,text/csv,.txt" onChange={pick} aria-label="Choose CSV file" />
          <select value={mode} onChange={(e) => setMode(e.target.value)} aria-label="What to do with items that already exist">
            <option value="add_update">Add new items and update existing ones</option>
            <option value="add_only">Add new items only (skip existing)</option>
          </select>
        </div>
        {error && <p className="error">{error}</p>}

        {res && (
          <>
            <p>
              <Badge kind="green">{res.created} new</Badge> <Badge kind="blue">{res.updated} to update</Badge>{' '}
              <Badge>{res.unchanged} unchanged</Badge> {res.skipped > 0 && <Badge>{res.skipped} skipped</Badge>}{' '}
              {res.error_count > 0 && <Badge kind="red">{res.error_count} with errors</Badge>}
            </p>
            {res.error_count > 0 && (
              <div className="notice">
                <strong>Fix these rows in the file and choose it again. Nothing is saved until every row is correct.</strong>
                <ul className="plain">{res.errors.slice(0, 8).map((er) => <li key={er.line}><span>Row {er.line}</span><span>{er.message}</span></li>)}</ul>
                {res.error_count > 8 && <span className="muted small">and {res.error_count - 8} more</span>}
              </div>
            )}
            {res.preview.length > 0 && (
              <div className="table-wrap flat csv-preview">
                <table>
                  <thead><tr><th>Row</th><th>Item</th><th>Action</th><th>Total</th><th>Change</th></tr></thead>
                  <tbody>
                    {res.preview.slice(0, 40).map((p) => (
                      <tr key={p.line}><td>{p.line}</td><td>{p.name}</td><td><Badge kind={ACTION[p.action][0]}>{ACTION[p.action][1]}</Badge></td><td>{p.total}</td><td className="muted small">{p.changes}</td></tr>
                    ))}
                  </tbody>
                </table>
                {res.preview.length > 40 && <p className="muted small">Showing the first 40 rows.</p>}
              </div>
            )}
          </>
        )}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button type="button" className="btn" disabled={!ready || busy} onClick={save}>{busy ? 'Importing…' : ready ? `Import ${res.created + res.updated} item(s)` : 'Import'}</button>
        </div>
      </div>
    </Modal>
  );
}
