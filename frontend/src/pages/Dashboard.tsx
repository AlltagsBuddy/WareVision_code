import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { customersApi, stockApi } from '../api/client'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<{ customers: number; lowStock: number } | null>(null)

  useEffect(() => {
    Promise.all([customersApi.list({ limit: 100 }), stockApi.lowStock()])
      .then(([customers, lowStock]) =>
        setStats({ customers: customers.length, lowStock: lowStock.length })
      )
      .catch(() => setStats({ customers: 0, lowStock: 0 }))
  }, [])

  return (
    <div className="page">
      <h1>Willkommen, {user?.first_name}</h1>
      <div className="dashboard-cards">
        <Link to="/customers" className="card">
          <h3>Kunden</h3>
          <p>{stats?.customers ?? '–'}</p>
        </Link>
        <Link to="/stock" className="card warning">
          <h3>Mindestbestand</h3>
          <p>{stats?.lowStock ?? '–'} Artikel unter Mindestbestand</p>
        </Link>
      </div>
    </div>
  )
}
