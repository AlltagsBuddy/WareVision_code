import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { customersApi, stockApi, workshopOrdersApi, appointmentsApi, invoicesApi } from '../api/client'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<{ customers: number; lowStock: number; workshopOrders: number; appointments: number; invoices: number } | null>(null)

  useEffect(() => {
    const today = new Date()
    const weekStart = new Date(today)
    weekStart.setDate(today.getDate() - today.getDay() + 1)
    weekStart.setHours(0, 0, 0, 0)
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekStart.getDate() + 6)
    weekEnd.setHours(23, 59, 59, 999)
    Promise.all([
      customersApi.list({ limit: 100 }),
      stockApi.lowStock(),
      workshopOrdersApi.list({ limit: 100 }),
      appointmentsApi.list({ from_date: weekStart.toISOString(), to_date: weekEnd.toISOString() }),
      invoicesApi.list({ limit: 100 }),
    ])
      .then(([customers, lowStock, orders, apts, invs]) =>
        setStats({
          customers: customers.length,
          lowStock: lowStock.length,
          workshopOrders: orders.length,
          appointments: apts.filter((a: any) => a.status !== 'cancelled').length,
          invoices: invs.length,
        })
      )
      .catch(() => setStats({ customers: 0, lowStock: 0, workshopOrders: 0, appointments: 0, invoices: 0 }))
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
          <p>{stats?.workshopOrders ?? '–'}</p>
        </Link>
        <Link to="/appointments" className="card">
          <h3>Termine diese Woche</h3>
          <p>{stats?.appointments ?? '–'}</p>
        </Link>
        <Link to="/invoices" className="card">
          <h3>Rechnungen</h3>
          <p>{stats?.invoices ?? '–'}</p>
        </Link>
        <Link to="/stock" className="card warning">
          <h3>Mindestbestand</h3>
          <p>{stats?.lowStock ?? '–'} Artikel unter Mindestbestand</p>
        </Link>
      </div>
    </div>
  )
}
