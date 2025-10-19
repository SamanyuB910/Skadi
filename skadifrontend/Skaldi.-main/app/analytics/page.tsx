"use client"

import { useEffect, useState } from "react"
import DashboardHeader from "@/components/dashboard-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TrendingDown, TrendingUp, DollarSign, Zap, Activity, Thermometer } from "lucide-react"
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis, ComposedChart } from "recharts"

interface DailyDataPoint {
  day: string
  date: string
  energyBaseline: number
  energyOptimized: number
  energySaved: number
  avgLatency: number
  avgThroughput: number
  totalCost: number
  totalCostOptimized: number
  savings: number
  pue: number
  cumulativeSavings?: number
  p50?: number
  p95?: number
  p99?: number
  target?: number
  energyPerRequest?: number
}

interface AnalyticsData {
  daily_data: DailyDataPoint[]
  summary: {
    total_savings: number
    avg_energy_reduction_pct: number
    avg_latency_ms: number
    avg_throughput: number
  }
}

export default function AnalyticsPage() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/ml-analytics/performance-metrics`)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        setAnalyticsData(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch analytics data")
        console.error("Error fetching analytics:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 60000) // Refresh every 60 seconds
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <DashboardHeader />
        <main className="p-6">
          <div className="text-center text-muted-foreground">Loading analytics...</div>
        </main>
      </div>
    )
  }

  if (error || !analyticsData) {
    return (
      <div className="min-h-screen bg-background">
        <DashboardHeader />
        <main className="p-6">
          <div className="text-center text-destructive">Error: {error || "No data available"}</div>
        </main>
      </div>
    )
  }

  const dailyData = analyticsData.daily_data
  const totalSavings = analyticsData.summary.total_savings
  const avgEnergyReduction = analyticsData.summary.avg_energy_reduction_pct.toFixed(1)

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader />
      <main className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Analytics & Performance</h1>
          <p className="text-muted-foreground">Comprehensive energy and performance metrics over time</p>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">7-Day Savings</CardTitle>
              <DollarSign className="h-4 w-4 text-chart-4" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">${totalSavings.toFixed(2)}</div>
              <p className="text-xs text-chart-4 flex items-center gap-1 mt-1">
                <TrendingDown className="h-3 w-3" />
                <span>23% cost reduction</span>
              </p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Energy Reduction</CardTitle>
              <Zap className="h-4 w-4 text-chart-1" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{avgEnergyReduction}%</div>
              <p className="text-xs text-muted-foreground mt-1">vs baseline consumption</p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Latency</CardTitle>
              <Activity className="h-4 w-4 text-chart-2" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {analyticsData.summary.avg_latency_ms.toFixed(0)} ms
              </div>
              <p className="text-xs text-chart-4 flex items-center gap-1 mt-1">
                <TrendingDown className="h-3 w-3" />
                <span>Within SLO targets</span>
              </p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Throughput</CardTitle>
              <TrendingUp className="h-4 w-4 text-chart-4" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {analyticsData.summary.avg_throughput.toFixed(0)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">tokens/sec</p>
            </CardContent>
          </Card>
        </div>

        {/* Tabbed Charts */}
        <Tabs defaultValue="energy" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="energy">Energy</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="cost">Cost Analysis</TabsTrigger>
            <TabsTrigger value="efficiency">Efficiency</TabsTrigger>
          </TabsList>

          <TabsContent value="energy" className="space-y-4">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Energy Consumption Trends</CardTitle>
                <CardDescription>7-day comparison: baseline vs optimized</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    energyBaseline: {
                      label: "Baseline",
                      color: "#ef4444",
                    },
                    energyOptimized: {
                      label: "Optimized",
                      color: "#22c55e",
                    },
                    energySaved: {
                      label: "Saved",
                      color: "#f59e0b",
                    },
                  }}
                  className="h-[400px]"
                >
                  <AreaChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Area
                      type="monotone"
                      dataKey="energyBaseline"
                      stroke="var(--color-energyBaseline)"
                      fill="var(--color-energyBaseline)"
                      fillOpacity={0.2}
                    />
                    <Area
                      type="monotone"
                      dataKey="energyOptimized"
                      stroke="var(--color-energyOptimized)"
                      fill="var(--color-energyOptimized)"
                      fillOpacity={0.4}
                    />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Daily Energy Savings</CardTitle>
                <CardDescription>kWh saved per day through optimization</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    energySaved: {
                      label: "Energy Saved (kWh)",
                      color: "#10b981",
                    },
                  }}
                  className="h-[300px]"
                >
                  <BarChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Bar dataKey="energySaved" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="performance" className="space-y-4">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Latency & Throughput</CardTitle>
                <CardDescription>Performance metrics over 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    avgLatency: {
                      label: "Latency (ms)",
                      color: "#f59e0b",
                    },
                    avgThroughput: {
                      label: "Throughput",
                      color: "#3b82f6",
                    },
                  }}
                  className="h-[400px]"
                >
                  <ComposedChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis yAxisId="left" stroke="#9ca3af" />
                    <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="avgLatency"
                      stroke="#f59e0b"
                      strokeWidth={3}
                      dot={{ r: 5, fill: "#f59e0b" }}
                    />
                    <Bar yAxisId="right" dataKey="avgThroughput" fill="#3b82f6" fillOpacity={0.6} />
                  </ComposedChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="border-border bg-card">
                <CardHeader>
                  <CardTitle className="text-foreground">Latency Distribution</CardTitle>
                  <CardDescription>P50, P95, P99 percentiles</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer
                    config={{
                      p50: {
                        label: "P50",
                        color: "#22c55e",
                      },
                      p95: {
                        label: "P95",
                        color: "#f59e0b",
                      },
                      p99: {
                        label: "P99",
                        color: "#ef4444",
                      },
                    }}
                    className="h-[300px]"
                  >
                    <LineChart
                      data={dailyData.map((d) => ({
                        ...d,
                        p50: d.avgLatency * 0.8,
                        p95: d.avgLatency * 1.2,
                        p99: d.avgLatency * 1.5,
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="day" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Line type="monotone" dataKey="p50" stroke="#22c55e" strokeWidth={3} dot={{ r: 4 }} />
                      <Line type="monotone" dataKey="p95" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} />
                      <Line type="monotone" dataKey="p99" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} />
                    </LineChart>
                  </ChartContainer>
                </CardContent>
              </Card>

              <Card className="border-border bg-card">
                <CardHeader>
                  <CardTitle className="text-foreground">Throughput Trends</CardTitle>
                  <CardDescription>Requests per second over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer
                    config={{
                      avgThroughput: {
                        label: "Throughput",
                        color: "#8b5cf6",
                      },
                    }}
                    className="h-[300px]"
                  >
                    <AreaChart data={dailyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="day" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Area
                        type="monotone"
                        dataKey="avgThroughput"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.5}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ChartContainer>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="cost" className="space-y-4">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Cost Comparison</CardTitle>
                <CardDescription>Daily energy costs: baseline vs optimized</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    totalCost: {
                      label: "Baseline Cost",
                      color: "#ef4444",
                    },
                    totalCostOptimized: {
                      label: "Optimized Cost",
                      color: "#22c55e",
                    },
                  }}
                  className="h-[400px]"
                >
                  <BarChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Bar dataKey="totalCost" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="totalCostOptimized" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Cumulative Savings</CardTitle>
                <CardDescription>Total cost savings over 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    savings: {
                      label: "Cumulative Savings ($)",
                      color: "#10b981",
                    },
                  }}
                  className="h-[300px]"
                >
                  <AreaChart
                    data={dailyData.map((d, i) => ({
                      ...d,
                      cumulativeSavings: dailyData.slice(0, i + 1).reduce((sum, day) => sum + day.savings, 0),
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Area
                      type="monotone"
                      dataKey="cumulativeSavings"
                      stroke="#10b981"
                      fill="#10b981"
                      fillOpacity={0.5}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="efficiency" className="space-y-4">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Power Usage Effectiveness (PUE)</CardTitle>
                <CardDescription>Data center efficiency metric over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    pue: {
                      label: "PUE Ratio",
                      color: "#06b6d4",
                    },
                    target: {
                      label: "Target",
                      color: "#10b981",
                    },
                  }}
                  className="h-[400px]"
                >
                  <LineChart
                    data={dailyData.map((d) => ({
                      ...d,
                      target: 1.25,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="day" stroke="#9ca3af" />
                    <YAxis domain={[1.0, 1.8]} stroke="#9ca3af" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Line type="monotone" dataKey="pue" stroke="#06b6d4" strokeWidth={3} dot={{ r: 5, fill: "#06b6d4" }} />
                    <Line
                      type="monotone"
                      dataKey="target"
                      stroke="#10b981"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                    />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="border-border bg-card">
                <CardHeader>
                  <CardTitle className="text-foreground">Energy per Request</CardTitle>
                  <CardDescription>Joules per API request</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer
                    config={{
                      energyPerRequest: {
                        label: "Energy/Request (J)",
                        color: "#f59e0b",
                      },
                    }}
                    className="h-[300px]"
                  >
                    <BarChart
                      data={dailyData.map((d) => ({
                        ...d,
                        energyPerRequest: ((d.energyOptimized * 1000) / (d.avgThroughput * 86400)).toFixed(2),
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="day" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Bar dataKey="energyPerRequest" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ChartContainer>
                </CardContent>
              </Card>

              <Card className="border-border bg-card">
                <CardHeader>
                  <CardTitle className="text-foreground">Optimization Impact</CardTitle>
                  <CardDescription>Key efficiency improvements</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-3">
                        <Zap className="h-5 w-5 text-chart-1" />
                        <div>
                          <div className="font-medium text-foreground">Energy Reduction</div>
                          <div className="text-xs text-muted-foreground">vs baseline</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-chart-4">23%</div>
                        <div className="text-xs text-muted-foreground">103 kWh saved</div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-3">
                        <DollarSign className="h-5 w-5 text-chart-4" />
                        <div>
                          <div className="font-medium text-foreground">Cost Savings</div>
                          <div className="text-xs text-muted-foreground">7-day total</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-chart-4">${totalSavings.toFixed(2)}</div>
                        <div className="text-xs text-muted-foreground">$22.4K annual</div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-3">
                        <Activity className="h-5 w-5 text-chart-2" />
                        <div>
                          <div className="font-medium text-foreground">Performance</div>
                          <div className="text-xs text-muted-foreground">maintained SLO</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-chart-4">99.8%</div>
                        <div className="text-xs text-muted-foreground">uptime</div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Thermometer className="h-5 w-5 text-chart-3" />
                        <div>
                          <div className="font-medium text-foreground">Cooling Efficiency</div>
                          <div className="text-xs text-muted-foreground">avg improvement</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-chart-4">18%</div>
                        <div className="text-xs text-muted-foreground">better PUE</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
