"use client"

import MetallicPaint, { parseLogoImage } from "./MetallicPaint"
import { useState, useEffect } from "react"

export default function SkadiLogoLoader() {
  const [imageData, setImageData] = useState<ImageData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadSkadiLogo() {
      try {
        console.log("[v0] Starting to load SKADI logo")

        const svgContent = `
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 150" width="600" height="150">
            <defs>
              <style>
                text { 
                  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
                  font-weight: 900;
                  font-size: 100px;
                  letter-spacing: 4px;
                }
              </style>
            </defs>
            <!-- Snowflake icon -->
            <g transform="translate(30, 75)">
              <path d="M0,-25 L0,25 M-25,0 L25,0 M-18,-18 L18,18 M-18,18 L18,-18" 
                    stroke="black" strokeWidth="6" strokeLinecap="round"/>
              <circle cx="0" cy="-25" r="3" fill="black"/>
              <circle cx="0" cy="25" r="3" fill="black"/>
              <circle cx="-25" cy="0" r="3" fill="black"/>
              <circle cx="25" cy="0" r="3" fill="black"/>
              <circle cx="-18" cy="-18" r="3" fill="black"/>
              <circle cx="18" cy="18" r="3" fill="black"/>
              <circle cx="-18" cy="18" r="3" fill="black"/>
              <circle cx="18" cy="-18" r="3" fill="black"/>
            </g>
            <!-- SKADI text with thick stroke -->
            <text x="80" y="105" fill="black" stroke="black" strokeWidth="2">SKADI</text>
          </svg>
        `

        console.log("[v0] Creating SVG blob")
        const blob = new Blob([svgContent], { type: "image/svg+xml" })
        const file = new File([blob], "skadi-logo.svg", { type: "image/svg+xml" })

        console.log("[v0] Parsing logo image")
        const parsedData = await parseLogoImage(file)

        console.log("[v0] Parsed data:", parsedData)

        if (parsedData?.imageData) {
          console.log("[v0] Successfully loaded SKADI logo")
          setImageData(parsedData.imageData)
        } else {
          console.error("[v0] No image data returned from parseLogoImage")
          setError("Failed to parse logo")
        }
      } catch (err) {
        console.error("[v0] Error loading SKADI logo:", err)
        setError(err instanceof Error ? err.message : "Unknown error")
      }
    }

    loadSkadiLogo()
  }, [])

  if (error) {
    return <div className="w-full h-full flex items-center justify-center text-red-500">Error: {error}</div>
  }

  if (!imageData) {
    return <div className="w-full h-full flex items-center justify-center text-white text-2xl">Loading...</div>
  }

  console.log("[v0] Rendering MetallicPaint with imageData")

  return (
    <div className="w-full h-full">
      <MetallicPaint
        imageData={imageData}
        params={{
          edge: 2,
          patternBlur: 0.005,
          patternScale: 2,
          refraction: 0.015,
          speed: 0.3,
          liquid: 0.07,
        }}
      />
    </div>
  )
}
