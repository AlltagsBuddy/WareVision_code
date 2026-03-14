import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { customersApi, stockApi, workshopOrdersApi, appointmentsApi, invoicesApi, maintenancePlansApi } from '../api/client'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<{ customers: number; lowStock: number; workshopOrders: number; appointments: number; invoices: number; overdueInvoices: number; maintenancePlans: number } | null>(null)

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
      invoicesApi.list({ overdue: true }),
      maintenancePlansApi.list(),
    ])
      .then(([customers, lowStock, orders, apts, invs, overdueInvs, plans]) =>
        setStats({
          customers: customers.length,
          lowStock: lowStock.length,
          workshopOrders: orders.length,
          appointments: apts.filter((a: any) => a.status !== 'cancelled').length,
          invoices: invs.length,
          overdueInvoices: overdueInvs.length,
          maintenancePlans: plans.length,
        })
      )
      .catch(() => setStats({ customers: 0, lowStock: 0, workshopOrders: 0, appointments: 0, invoices: 0, overdueInvoices: 0, maintenancePlans: 0 }))
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
        {stats && stats.overdueInvoices > 0 && (
          <Link to="/invoices?overdue=1" className="card warning">
            <h3>Überfällig</h3>
            <p>{stats.overdueInvoices} Rechnung(en)</p>
          </Link>
        )}
        <Link to="/stock" className="card warning">
          <h3>Mindestbestand</h3>
          <p>{stats?.lowStock ?? '–'} Artikel unter Mindestbestand</p>
        </Link>
        <Link to="/maintenance-plans" className="card">
          <h3>Wartungspläne</h3>
          <p>{stats?.maintenancePlans ?? '–'}</p>
        </Link>
      </div>
    </div>
  )
}
