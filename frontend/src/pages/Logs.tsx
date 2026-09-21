import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";

export default function Logs() {
  const [rows, setRows] = useState<Array<Record<string, string>>>([]);
  const [action, setAction] = useState("");
  const [resource, setResource] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  async function load(event?: FormEvent) {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (resource) params.set("resource_type", resource);
    if (dateFrom) params.set("date_from", new Date(dateFrom).toISOString());
    if (dateTo) params.set("date_to", new Date(dateTo).toISOString());
    setRows(await api.logs(params));
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Audit napló</h2>
          <p>Minden lényeges módosítás nyomon követhető.</p>
        </div>
      </div>
      <form className="card row" onSubmit={load} style={{ marginBottom: 16, padding: 16 }}>
        <input placeholder="action" value={action} onChange={(e) => setAction(e.target.value)} />
        <input placeholder="resource" value={resource} onChange={(e) => setResource(e.target.value)} />
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <button className="btn" type="submit">Szűrés</button>
      </form>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Idő</th>
              <th>Felhasználó</th>
              <th>Action</th>
              <th>Erőforrás</th>
              <th>Részletek</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.timestamp}</td>
                <td>{row.user}</td>
                <td>{row.action}</td>
                <td>
                  {row.resource_type} {row.resource_id}
                </td>
                <td>{row.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
