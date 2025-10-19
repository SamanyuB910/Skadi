"use client"

import { Snowflake } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export default function DashboardHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <Snowflake className="h-6 w-6 text-cyan-500" strokeWidth={1.5} />
          <span className="text-xl font-light tracking-tight">Skadi</span>
        </Link>

        <nav className="flex items-center gap-1">
          <Link href="/">
            <Button variant="ghost" size="sm">
              Overview
            </Button>
          </Link>
          <Link href="/heat-map">
            <Button variant="ghost" size="sm">
              Heat Map
            </Button>
          </Link>
          <Link href="/analytics">
            <Button variant="ghost" size="sm">
              Analytics
            </Button>
          </Link>
        </nav>
      </div>
    </header>
  )
}
