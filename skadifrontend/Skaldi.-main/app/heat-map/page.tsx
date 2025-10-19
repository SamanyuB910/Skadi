"use client"

import { useEffect, useState } from "react"
import DashboardHeader from "@/components/dashboard-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Thermometer, AlertTriangle, CheckCircle2, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

// Types for API response
interface RackData {
  id: string
  row: number
  col: number
  temp: number
  deviation: number
  status: "nominal" | "warning" | "critical"
  load: number
  metrics: {
    inlet_c: number
    outlet_c: number
    delta_t: number
    pdu_kw: number
    tokens_ps: number
    latency_p95_ms: number
    queue_depth: number
    fan_rpm_pct: number
    pump_rpm_pct: number
  }
}

interface HeatmapData {
  timestamp: string
  model_info: {
    model_name: string
    loaded_at: string
    tau_fast: number
    tau_persist: number
    features: string[]
    n_clusters: number
  }
  racks: RackData[]
  stats: {
    avg_temp: number
    min_temp: number
    max_temp: number
    avg_deviation: number
    min_deviation: number
    max_deviation: number
    hotspots: number
    coolzones: number
    total_racks: number
    status_distribution: {
      nominal: number
      warning: number
      critical: number
    }
  }
  thresholds: {
    tau_fast: number
    tau_persist: number
    tau_fast_adjusted: number
    tau_persist_adjusted: number
  }
}

const getColorForTemp = (temp: number) => {
  if (temp < 22) return "bg-blue-500/80"
  if (temp < 23) return "bg-blue-400/80"
  if (temp < 24) return "bg-cyan-400/80"
  if (temp < 25) return "bg-green-400/80"
  if (temp < 26) return "bg-yellow-400/80"
  if (temp < 27) return "bg-orange-400/80"
  return "bg-red-500/80"
}

export default function HeatMapPage() {
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch heatmap data from backend
  useEffect(() => {
    const fetchHeatmapData = async () => {
      try {
        setLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/ml-heatmap/ims-anomaly`)
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }
        const data: HeatmapData = await response.json()
        setHeatmapData(data)
        setError(null)
      } catch (err) {
        console.error("Failed to fetch heatmap data:", err)
        setError(err instanceof Error ? err.message : "Failed to load heatmap data")
      } finally {
        setLoading(false)
      }
    }

    fetchHeatmapData()
    // Refresh every 30 seconds
    const interval = setInterval(fetchHeatmapData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !heatmapData) {
    return (
      <div className="min-h-screen bg-background">
        <DashboardHeader />
        <main className="p-6 max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <p className="text-muted-foreground">Loading heatmap data...</p>
          </div>
        </main>
      </div>
    )
  }

  if (error && !heatmapData) {
    return (
      <div className="min-h-screen bg-background">
        <DashboardHeader />
        <main className="p-6 max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-orange-400 mx-auto mb-4" />
              <p className="text-muted-foreground">Error: {error}</p>
              <p className="text-sm text-muted-foreground mt-2">Make sure the backend is running on port 8000</p>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (!heatmapData) {
    return null
  }

  const { racks, stats } = heatmapData
  const hotspots = racks.filter((r) => r.status === "warning" || r.status === "critical")
  const coolzones = racks.filter((r) => r.status === "nominal")
  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader />
      <main className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-light tracking-tight mb-2">Server Room Heat Map</h1>
          <p className="text-muted-foreground">Real-time thermal monitoring via NASA FOSS</p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Average Temp</CardTitle>
              <Thermometer className="h-4 w-4 text-cyan-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{stats.avg_temp}°C</div>
              <p className="text-xs text-green-500 flex items-center gap-1 mt-1">
                <TrendingDown className="h-3 w-3" />
                <span>-0.8°C from target</span>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Hot Spots</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{hotspots.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Racks above threshold</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Cool Zones</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-cyan-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{coolzones.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Racks in nominal range</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">FOSS Sensors</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{stats.total_racks}</div>
              <p className="text-xs text-green-500 flex items-center gap-1 mt-1">
                <CheckCircle2 className="h-3 w-3" />
                <span>All operational</span>
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Heat Map */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Thermal Distribution Map</CardTitle>
                <CardDescription>Live temperature readings across all server racks</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                  Cool
                </Badge>
                <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                  Optimal
                </Badge>
                <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">
                  Hot
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* Column headers */}
              <div className="flex gap-2 mb-2">
                <div className="w-12 text-xs font-medium text-muted-foreground"></div>
                {Array.from({ length: 12 }, (_, i) => (
                  <div key={i} className="flex-1 text-center text-xs font-medium text-muted-foreground">
                    {i + 1}
                  </div>
                ))}
              </div>

              {/* Rack grid */}
              {Array.from({ length: 8 }, (_, row) => (
                <div key={row} className="flex gap-2">
                  <div className="w-12 flex items-center justify-center text-xs font-medium text-muted-foreground">
                    {String.fromCharCode(65 + row)}
                  </div>
                  {Array.from({ length: 12 }, (_, col) => {
                    const rack = racks.find((r) => r.row === row && r.col === col)
                    return (
                      <div
                        key={col}
                        className={cn(
                          "flex-1 aspect-square rounded border border-border/50 flex flex-col items-center justify-center text-xs font-medium transition-all hover:scale-105 hover:z-10 hover:shadow-lg cursor-pointer",
                          rack && getColorForTemp(rack.temp),
                        )}
                        title={`${rack?.id}: ${rack?.temp}°C, Load: ${rack?.load}%, Status: ${rack?.status}`}
                      >
                        <span className="text-background font-semibold">{rack?.temp}°</span>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-400" />
              Hot Spot Alerts
            </CardTitle>
            <CardDescription>Racks requiring attention ({stats.status_distribution.warning} warnings, {stats.status_distribution.critical} critical)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {hotspots.slice(0, 5).map((rack) => (
                <div
                  key={rack.id}
                  className="flex items-center justify-between text-sm border-b border-border pb-3 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "h-2 w-2 rounded-full",
                      rack.status === "critical" ? "bg-red-500" : "bg-orange-400"
                    )} />
                    <div>
                      <div className="font-medium">Rack {rack.id}</div>
                      <div className="text-xs text-muted-foreground">{rack.load}% load · Deviation: {rack.deviation}</div>
                    </div>
                  </div>
                  <span className={cn(
                    "font-semibold",
                    rack.status === "critical" ? "text-red-400" : "text-orange-400"
                  )}>{rack.temp}°C</span>
                </div>
              ))}
              {hotspots.length === 0 && (
                <div className="text-center text-muted-foreground py-4">
                  <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p>All racks operating normally</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
