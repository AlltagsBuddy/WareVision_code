/** Baujahr-Bereich eines Wartungsplans lesbar darstellen. */
export function buildYearLabel(p: { build_year_from?: number | null; build_year_to?: number | null }): string {
  const from = p.build_year_from
  const to = p.build_year_to
  if (from != null && to != null) return from === to ? String(from) : `${from}–${to}`
  if (from != null) return `ab ${from}`
  if (to != null) return `bis ${to}`
  return 'alle'
}
