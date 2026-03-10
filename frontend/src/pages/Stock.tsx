import { useEffect, useState } from 'react'
import { stockApi } from '../api/client'

export default function Stock() {
  const [lowStock, setLowStock] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    stockApi.lowStock().then(setLowStock).finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <h1>Lager</h1>
      <h2>Mindestbestand</h2>
      {loading ? (
        <p>Laden...</p>
      ) : lowStock.length === 0 ? (
        <p>Keine Artikel unter Mindestbestand.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Artikelnummer</th>
              <th>Name</th>
              <th>Bestand</th>
              <th>Mindestbestand</th>
            </tr>
          </thead>
          <tbody>
            {lowStock.map((a) => (
              <tr key={a.id}>
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td className="warning">{a.stock_quantity}</td>
                <td>{a.minimum_stock}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
