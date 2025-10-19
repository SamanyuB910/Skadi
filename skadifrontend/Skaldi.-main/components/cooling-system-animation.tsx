"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wind, Thermometer, Zap, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

interface CRACUnit {
  id: number
  x: number
  y: number
  power: number
  temp: number
  status: "active" | "idle" | "optimizing"
}

interface AirParticle {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  temp: number
}

export default function CoolingSystemAnimation() {
  const [cracUnits] = useState<CRACUnit[]>([
    { id: 1, x: 10, y: 10, power: 85, temp: 18, status: "active" },
    { id: 2, x: 50, y: 10, power: 72, temp: 19, status: "active" },
    { id: 3, x: 90, y: 10, power: 68, temp: 18.5, status: "optimizing" },
    { id: 4, x: 10, y: 90, power: 45, temp: 20, status: "idle" },
    { id: 5, x: 50, y: 90, power: 78, temp: 18, status: "active" },
    { id: 6, x: 90, y: 90, power: 81, temp: 19, status: "active" },
  ])

  const [particles, setParticles] = useState<AirParticle[]>([])
  const [time, setTime] = useState(0)

  useEffect(() => {
    // Initialize particles
    const initialParticles: AirParticle[] = []
    for (let i = 0; i < 50; i++) {
      initialParticles.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        temp: 18 + Math.random() * 4,
      })
    }
    setParticles(initialParticles)

    // Animation loop
    const interval = setInterval(() => {
      setTime((t) => t + 1)
      setParticles((prev) =>
        prev.map((p) => {
          let newX = p.x + p.vx
          let newY = p.y + p.vy

          // Bounce off walls
          if (newX < 0 || newX > 100) p.vx *= -1
          if (newY < 0 || newY > 100) p.vy *= -1

          newX = Math.max(0, Math.min(100, newX))
          newY = Math.max(0, Math.min(100, newY))

          return { ...p, x: newX, y: newY }
        }),
      )
    }, 50)

    return () => clearInterval(interval)
  }, [])

  const getParticleColor = (temp: number) => {
    if (temp < 19) return "bg-blue-400"
    if (temp < 20) return "bg-cyan-400"
    if (temp < 21) return "bg-green-400"
    return "bg-yellow-400"
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-500"
      case "optimizing":
        return "bg-yellow-500"
      case "idle":
        return "bg-gray-500"
      default:
        return "bg-gray-500"
    }
  }

  return (
    <div className="space-y-4">
      {/* Control Panel */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Cooling</CardTitle>
            <Wind className="h-4 w-4 text-chart-2" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">429 kW</div>
            <p className="text-xs text-chart-4 mt-1">-12% optimized</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Supply Temp</CardTitle>
            <Thermometer className="h-4 w-4 text-chart-1" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">18.8°C</div>
            <p className="text-xs text-muted-foreground mt-1">Target: 18-20°C</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Units</CardTitle>
            <Activity className="h-4 w-4 text-chart-4" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">5/6</div>
            <p className="text-xs text-muted-foreground mt-1">1 unit idle</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Efficiency</CardTitle>
            <Zap className="h-4 w-4 text-chart-4" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">2.8</div>
            <p className="text-xs text-chart-4 mt-1">PUE ratio</p>
          </CardContent>
        </Card>
      </div>

      {/* Animation Canvas */}
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-foreground">Live Airflow Visualization</CardTitle>
          <CardDescription>Real-time cooling distribution across data center floor</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative w-full aspect-video bg-gradient-to-b from-background to-muted rounded-lg border border-border overflow-hidden">
            {/* CRAC Units */}
            {cracUnits.map((unit) => (
              <div
                key={unit.id}
                className="absolute"
                style={{
                  left: `${unit.x}%`,
                  top: `${unit.y}%`,
                  transform: "translate(-50%, -50%)",
                }}
              >
                <div className="relative">
                  {/* Unit body */}
                  <div className="w-16 h-16 bg-card border-2 border-primary rounded-lg flex flex-col items-center justify-center shadow-lg">
                    <Wind className="h-6 w-6 text-primary animate-pulse" />
                    <span className="text-xs font-bold text-foreground mt-1">{unit.id}</span>
                  </div>

                  {/* Status indicator */}
                  <div
                    className={cn(
                      "absolute -top-1 -right-1 w-3 h-3 rounded-full",
                      getStatusColor(unit.status),
                      unit.status === "active" && "animate-pulse",
                    )}
                  />

                  {/* Airflow waves */}
                  {unit.status === "active" && (
                    <>
                      <div
                        className="absolute inset-0 border-2 border-primary/30 rounded-full animate-ping"
                        style={{ animationDuration: "2s" }}
                      />
                      <div
                        className="absolute inset-0 border-2 border-primary/20 rounded-full animate-ping"
                        style={{ animationDuration: "3s", animationDelay: "0.5s" }}
                      />
                    </>
                  )}

                  {/* Info tooltip */}
                  <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 bg-card border border-border rounded px-2 py-1 text-xs whitespace-nowrap shadow-lg">
                    <div className="text-foreground font-medium">{unit.power}% power</div>
                    <div className="text-muted-foreground">{unit.temp}°C</div>
                  </div>
                </div>
              </div>
            ))}

            {/* Air particles */}
            {particles.map((particle) => (
              <div
                key={particle.id}
                className={cn(
                  "absolute w-2 h-2 rounded-full transition-all duration-100",
                  getParticleColor(particle.temp),
                )}
                style={{
                  left: `${particle.x}%`,
                  top: `${particle.y}%`,
                  opacity: 0.6,
                  boxShadow: "0 0 4px currentColor",
                }}
              />
            ))}

            {/* Server racks (simplified) */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="grid grid-cols-4 gap-4">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    className="w-12 h-20 bg-muted/50 border border-border rounded flex items-center justify-center"
                  >
                    <Activity className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 right-4 bg-card/90 backdrop-blur border border-border rounded-lg p-3 space-y-2">
              <div className="text-xs font-medium text-foreground mb-2">Airflow Temperature</div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-3 h-3 rounded-full bg-blue-400" />
                <span className="text-muted-foreground">&lt;19°C</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-3 h-3 rounded-full bg-cyan-400" />
                <span className="text-muted-foreground">19-20°C</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="text-muted-foreground">20-21°C</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <span className="text-muted-foreground">&gt;21°C</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* CRAC Unit Details */}
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-foreground">CRAC Unit Status</CardTitle>
          <CardDescription>Individual unit performance metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {cracUnits.map((unit) => (
              <div key={unit.id} className="border border-border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wind className="h-4 w-4 text-primary" />
                    <span className="font-medium text-foreground">CRAC-{unit.id}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      unit.status === "active" && "bg-green-500/20 text-green-400 border-green-500/50",
                      unit.status === "optimizing" && "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
                      unit.status === "idle" && "bg-gray-500/20 text-gray-400 border-gray-500/50",
                    )}
                  >
                    {unit.status}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-muted-foreground">Power</div>
                    <div className="font-medium text-foreground">{unit.power}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Supply Temp</div>
                    <div className="font-medium text-foreground">{unit.temp}°C</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
