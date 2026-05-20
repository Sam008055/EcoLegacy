import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Echoes: Osho',
  description: 'An interactive digital avatar of Osho.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-black text-white antialiased min-h-screen" suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}
