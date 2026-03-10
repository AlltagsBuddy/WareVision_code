import { useEffect, useState } from 'react'
import { customersApi } from '../api/client'

export default function Customers() {
  const [customers, setCustomers] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    customersApi.list({ search: search || undefined }).then(setCustomers).finally(() => setLoading(false))
  }, [search])

  return (
    <div className="page">
      <h1>Kunden</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Suchen..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {loading ? (
        <p>Laden...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>E-Mail</th>
              <th>Telefon</th>
              <th>Typ</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>
                  {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'}
                </td>
                <td>{c.email || '–'}</td>
                <td>{c.phone || '–'}</td>
                <td>{c.customer_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
