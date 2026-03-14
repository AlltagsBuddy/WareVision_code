import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { dashboardApi } from '../api/client'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<{
    customers: number
    documents: number
    low_stock: number
    workshop_orders: number
    appointments_week: number
    appointments_today: number
    invoices: number
    overdue_invoices: number
    maintenance_plans: number
  } | null>(null)

  useEffect(() => {
    dashboardApi
      .getStats()
      .then((s) => setStats(s as NonNullable<typeof stats>))
      .catch(() =>
        setStats({
          customers: 0,
          documents: 0,
          low_stock: 0,
          workshop_orders: 0,
          appointments_week: 0,
          appointments_today: 0,
          invoices: 0,
          overdue_invoices: 0,
          maintenance_plans: 0,
        })
      )
  }, [])

  return (
    <div className="page">
      <h1>Willkommen, {user?.first_name}</h1>
      <div className="dashboard-cards">
        <Link to="/customers" className="card">
          <h3>Kunden</h3>
          <p>{stats?.customers ?? '–'}</p>
        </Link>
        <Link to="/workshop-orders" className="card">
          <h3>Werkstattaufträge</h3>
          <p>{stats?.workshop_orders ?? '–'}</p>
        </Link>
        <Link to="/appointments" className="card">
          <h3>Termine diese Woche</h3>
          <p>{stats?.appointments_week ?? '–'}</p>
        </Link>
        {stats && stats.appointments_today > 0 && (
          <Link to="/appointments" className="card">
            <h3>Termine heute</h3>
            <p>{stats.appointments_today}</p>
          </Link>
        )}
        <Link to="/invoices" className="card">
          <h3>Rechnungen</h3>
          <p>{stats?.invoices ?? '–'}</p>
        </Link>
        {stats && stats.overdue_invoices > 0 && (
          <Link to="/invoices?overdue=1" className="card warning">
            <h3>Überfällig</h3>
            <p>{stats.overdue_invoices} Rechnung(en)</p>
          </Link>
        )}
        {stats && stats.low_stock > 0 ? (
          <Link to="/stock" className="card warning">
            <h3>Mindestbestand</h3>
            <p>{stats.low_stock} Artikel unter Mindestbestand</p>
          </Link>
        ) : (
          <Link to="/stock" className="card">
            <h3>Mindestbestand</h3>
            <p>{stats?.low_stock ?? '–'} Artikel unter Mindestbestand</p>
          </Link>
        )}
        <Link to="/documents" className="card">
          <h3>Dokumente</h3>
          <p>{stats?.documents ?? '–'}</p>
        </Link>
        <Link to="/maintenance-plans" className="card">
          <h3>Wartungspläne</h3>
          <p>{stats?.maintenance_plans ?? '–'}</p>
        </Link>
      </div>
    </div>
  )
}
