import { describe, it, expect } from 'vitest'
import { buildYearLabel } from './buildYear'

describe('buildYearLabel', () => {
  it('zeigt Bereiche lesbar an', () => {
    expect(buildYearLabel({})).toBe('alle')
    expect(buildYearLabel({ build_year_from: null, build_year_to: null })).toBe('alle')
    expect(buildYearLabel({ build_year_to: 2012 })).toBe('bis 2012')
    expect(buildYearLabel({ build_year_from: 2013 })).toBe('ab 2013')
    expect(buildYearLabel({ build_year_from: 2005, build_year_to: 2012 })).toBe('2005–2012')
    expect(buildYearLabel({ build_year_from: 2010, build_year_to: 2010 })).toBe('2010')
  })
})
