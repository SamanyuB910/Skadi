"use client"
import { Snowflake } from "lucide-react"
import SplitText from "@/components/split-text"

export default function Page() {
  const getHeatColor = (row: number, col: number) => {
    const temp = Math.sin(row * 0.5 + col * 0.3 + Date.now() * 0.0005) * 0.5 + 0.5
    if (temp < 0.3) return "rgb(59, 130, 246)"
    if (temp < 0.5) return "rgb(34, 211, 238)"
    if (temp < 0.7) return "rgb(250, 204, 21)"
    return "rgb(239, 68, 68)"
  }

  const gridSize = 12
  const spacing = 80

  return (
    <main className="relative min-h-screen bg-black overflow-hidden">
      {/* 3D Grid Background */}
      <div className="absolute inset-0 flex items-center justify-center" style={{ perspective: "800px" }}>
        <div
          className="relative"
          style={{
            width: `${gridSize * spacing}px`,
            height: `${gridSize * spacing}px`,
            transform: `rotateX(60deg) translateY(-100px)`,
            transformStyle: "preserve-3d",
          }}
        >
          <svg
            className="absolute inset-0"
            width={gridSize * spacing}
            height={gridSize * spacing}
            style={{ transform: "translateZ(0px)" }}
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgb(34, 211, 238)" stopOpacity="0.8" />
                <stop offset="100%" stopColor="rgb(34, 211, 238)" stopOpacity="0.2" />
              </linearGradient>
            </defs>

            {Array.from({ length: gridSize + 1 }).map((_, i) => (
              <line
                key={`h-${i}`}
                x1="0"
                y1={i * spacing}
                x2={gridSize * spacing}
                y2={i * spacing}
                stroke="url(#lineGradient)"
                strokeWidth="1"
                opacity={0.4}
              />
            ))}

            {Array.from({ length: gridSize + 1 }).map((_, i) => (
              <line
                key={`v-${i}`}
                x1={i * spacing}
                y1="0"
                x2={i * spacing}
                y2={gridSize * spacing}
                stroke="url(#lineGradient)"
                strokeWidth="1"
                opacity={0.4}
              />
            ))}

            {Array.from({ length: gridSize + 1 }).map((_, row) =>
              Array.from({ length: gridSize + 1 }).map((_, col) => (
                <circle
                  key={`node-${row}-${col}`}
                  cx={col * spacing}
                  cy={row * spacing}
                  r="4"
                  fill={getHeatColor(row, col)}
                  opacity={0.8}
                  className="animate-pulse"
                  style={{
                    animationDelay: `${(row + col) * 0.1}s`,
                    animationDuration: "3s",
                  }}
                />
              )),
            )}
          </svg>
        </div>
      </div>

      <div className="absolute inset-0 bg-gradient-to-b from-black/90 via-black/30 to-black/90 pointer-events-none" />

      <article className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          <header className="mb-8">
            <h1 className="sr-only">Skadi - AI Data Center Cooling Optimization</h1>
            <div className="flex items-center justify-center gap-6 mb-4">
              <Snowflake className="w-16 h-16 text-cyan-400" strokeWidth={1.5} aria-hidden="true" />
              <SplitText
                text="SKADI"
                tag="h1"
                className="text-8xl font-black text-white tracking-wider"
                delay={100}
                duration={0.6}
                ease="power3.out"
                splitType="chars"
                from={{ opacity: 0, y: 40 }}
                to={{ opacity: 1, y: 0 }}
                threshold={0.1}
                rootMargin="-100px"
                textAlign="center"
              />
            </div>
          </header>

          <p className="text-2xl text-gray-300 mb-12 font-light">AI-powered data center cooling optimization</p>

          <nav className="flex gap-4" aria-label="Main navigation">
            <a
              href="/heat-map"
              className="px-8 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-semibold rounded-lg transition-colors"
            >
              Heat Map
            </a>
            <a
              href="/analytics"
              className="px-8 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-lg backdrop-blur-sm border border-white/20 transition-colors"
            >
              Analytics
            </a>
          </nav>
        </div>
      </article>
    </main>
  )
}
