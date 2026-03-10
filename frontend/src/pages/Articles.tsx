import { useEffect, useState } from 'react'
import { articlesApi } from '../api/client'

export default function Articles() {
  const [articles, setArticles] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    articlesApi.list({ search: search || undefined }).then(setArticles).finally(() => setLoading(false))
  }, [search])

  return (
    <div className="page">
      <h1>Artikel</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Artikelnummer oder Name..."
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
              <th>Art.-Nr.</th>
              <th>Name</th>
              <th>Bestand</th>
              <th>Mindestbestand</th>
              <th>VK B2C</th>
            </tr>
          </thead>
          <tbody>
            {articles.map((a) => (
              <tr key={a.id}>
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td>{a.stock_quantity}</td>
                <td>{a.minimum_stock}</td>
                <td>{Number(a.sales_price_b2c).toFixed(2)} €</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
