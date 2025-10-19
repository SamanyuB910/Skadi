"use client"

import { useEffect, useState } from "react"
import MetallicPaint from "./MetallicPaint"

export default function SnowflakeMetallic() {
  const [imageData, setImageData] = useState<ImageData | null>(null)

  useEffect(() => {
    // Create SVG for snowflake
    const svgString = `
      <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" x2="12" y1="2" y2="22"/>
        <path d="m12 2-7.5 4.5"/>
        <path d="m12 2 7.5 4.5"/>
        <path d="m12 22 7.5-4.5"/>
        <path d="m12 22-7.5-4.5"/>
        <line x1="2" x2="22" y1="12" y2="12"/>
        <path d="m2 12 4.5-7.5"/>
        <path d="m2 12 4.5 7.5"/>
        <path d="m22 12-4.5 7.5"/>
        <path d="m22 12-4.5-7.5"/>
        <line x1="6.34" x2="17.66" y1="6.34" y2="17.66"/>
        <path d="m6.34 6.34-2.12-2.12"/>
        <path d="m6.34 6.34-2.12 2.12"/>
        <path d="m17.66 17.66 2.12 2.12"/>
        <path d="m17.66 17.66 2.12-2.12"/>
        <line x1="6.34" x2="17.66" y1="17.66" y2="6.34"/>
        <path d="m6.34 17.66-2.12 2.12"/>
        <path d="m6.34 17.66-2.12-2.12"/>
        <path d="m17.66 6.34 2.12-2.12"/>
        <path d="m17.66 6.34 2.12 2.12"/>
      </svg>
    `

    const canvas = document.createElement("canvas")
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const img = new Image()
    const blob = new Blob([svgString], { type: "image/svg+xml" })
    const url = URL.createObjectURL(blob)

    img.onload = () => {
      const size = 200
      canvas.width = size
      canvas.height = size

      // Draw white background
      ctx.fillStyle = "white"
      ctx.fillRect(0, 0, size, size)

      // Draw snowflake in black
      ctx.fillStyle = "black"
      ctx.strokeStyle = "black"
      ctx.lineWidth = 3
      ctx.drawImage(img, 0, 0, size, size)

      const imgData = ctx.getImageData(0, 0, size, size)
      setImageData(imgData)
      URL.revokeObjectURL(url)
    }

    img.src = url
  }, [])

  if (!imageData) {
    return (
      <div className="w-16 h-16 flex items-center justify-center">
        <div className="animate-pulse text-cyan-400">❄</div>
      </div>
    )
  }

  return (
    <div className="w-16 h-16">
      <MetallicPaint imageData={imageData} />
    </div>
  )
}
