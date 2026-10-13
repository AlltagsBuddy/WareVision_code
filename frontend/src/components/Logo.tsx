interface LogoProps {
  /** header = Navigation, auth = Login/Registrierung */
  size?: 'header' | 'auth'
  className?: string
}

export default function Logo({ size = 'header', className = '' }: LogoProps) {
  return (
    <img
      src="/warevision-logo.png"
      alt="WareVision – Warenwirtschaft"
      className={`brand-logo brand-logo--${size} ${className}`.trim()}
    />
  )
}
