import { Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { useAuth } from './hooks/useAuth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Customers from './pages/Customers'
import Vehicles from './pages/Vehicles'
import Articles from './pages/Articles'
import Stock from './pages/Stock'
import WorkshopOrders from './pages/WorkshopOrders'
import Appointments from './pages/Appointments'
import Invoices from './pages/Invoices'
import Documents from './pages/Documents'
import MaintenancePlans from './pages/MaintenancePlans'
import Users from './pages/Users'
import Settings from './pages/Settings'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth()
  if (loading) return <div className="loading">Laden...</div>
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<Customers />} />
        <Route path="vehicles" element={<Vehicles />} />
        <Route path="articles" element={<Articles />} />
        <Route path="stock" element={<Stock />} />
        <Route path="workshop-orders" element={<WorkshopOrders />} />
        <Route path="appointments" element={<Appointments />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="documents" element={<Documents />} />
        <Route path="maintenance-plans" element={<MaintenancePlans />} />
        <Route path="users" element={<Users />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
