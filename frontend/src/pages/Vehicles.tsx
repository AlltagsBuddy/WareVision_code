import { useEffect, useState } from 'react'
import { vehiclesApi } from '../api/client'

export default function Vehicles() {
  const [vehicles, setVehicles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    vehiclesApi.list().then(setVehicles).finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <h1>Fahrzeuge</h1>
      {loading ? (
        <p>Laden...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Kennzeichen</th>
              <th>VIN</th>
              <th>Kategorie</th>
              <th>Baujahr</th>
              <th>Kilometer</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id}>
                <td>{v.license_plate || '–'}</td>
                <td>{v.vin || '–'}</td>
                <td>{v.category}</td>
                <td>{v.build_year || '–'}</td>
                <td>{v.mileage != null ? `${v.mileage} km` : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
