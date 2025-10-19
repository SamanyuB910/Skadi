import type React from "react"
import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Skadi - AI Data Center Cooling Optimization | NASA FOSS Technology",
  description:
    "Skadi uses NASA fiber-optic sensing (FOSS), Intelligent Monitoring System (IMS), and Model-based Monitoring System (MMS) to optimize data center cooling and reduce energy consumption by up to 30%. Real-time thermal monitoring and AI-powered optimization for sustainable data centers.",
  keywords: [
    "data center optimization",
    "AI cooling system",
    "NASA FOSS",
    "fiber optic sensing",
    "data center energy efficiency",
    "thermal monitoring",
    "IMS intelligent monitoring",
    "MMS model-based monitoring",
    "sustainable data centers",
    "server cooling optimization",
    "AI data center",
    "energy per prompt",
    "PUE optimization",
    "CRAC optimization",
  ],
  authors: [{ name: "Skadi Team" }],
  creator: "Skadi",
  publisher: "Skadi",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://skadi.ai",
    title: "Skadi - AI Data Center Cooling Optimization",
    description:
      "Reduce data center energy consumption by 30% with NASA-powered AI optimization. Real-time thermal monitoring and intelligent cooling control.",
    siteName: "Skadi",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Skadi AI Data Center Optimization Dashboard",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Skadi - AI Data Center Cooling Optimization",
    description: "Reduce data center energy by 30% with NASA-powered AI optimization",
    images: ["/og-image.png"],
    creator: "@skadi_ai",
  },
  alternates: {
    canonical: "https://skadi.ai",
  },
  generator: "v0.dev",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Skadi",
              applicationCategory: "BusinessApplication",
              description: "AI-powered data center cooling optimization using NASA fiber-optic sensing technology",
              operatingSystem: "Web",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
              },
              aggregateRating: {
                "@type": "AggregateRating",
                ratingValue: "4.8",
                ratingCount: "127",
              },
              creator: {
                "@type": "Organization",
                name: "Skadi",
                url: "https://skadi.ai",
              },
            }),
          }}
        />
      </head>
      <body className="font-sans">{children}</body>
    </html>
  )
}
