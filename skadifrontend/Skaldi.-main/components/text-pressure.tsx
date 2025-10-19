"use client"

import type React from "react"

import { useEffect, useRef, useState } from "react"

interface TextPressureProps {
  text: string
  fontFamily?: string
  fontUrl?: string
  flex?: boolean
  scale?: boolean
  alpha?: boolean
  stroke?: boolean
  width?: boolean
  weight?: boolean
  italic?: boolean
  textColor?: string
  strokeColor?: string
  className?: string
  minFontSize?: number
}

export function TextPressure({
  text,
  fontFamily = "system-ui",
  fontUrl,
  flex = true,
  scale = false,
  alpha = false,
  stroke = false,
  width = true,
  weight = true,
  italic = false,
  textColor = "#FFFFFF",
  strokeColor = "#FFFFFF",
  className = "",
  minFontSize = 24,
}: TextPressureProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [fontLoaded, setFontLoaded] = useState(!fontUrl)

  useEffect(() => {
    if (fontUrl && fontFamily) {
      const font = new FontFace(fontFamily, `url(${fontUrl})`)
      font
        .load()
        .then((loadedFont) => {
          document.fonts.add(loadedFont)
          setFontLoaded(true)
        })
        .catch((error) => {
          console.error("Font loading failed:", error)
          setFontLoaded(true)
        })
    }
  }, [fontUrl, fontFamily])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setMousePos({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        })
      }
    }

    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [])

  const getCharStyle = (index: number, charRef: HTMLSpanElement | null) => {
    if (!charRef || !fontLoaded) return {}

    const rect = charRef.getBoundingClientRect()
    const charX = rect.left + rect.width / 2
    const charY = rect.top + rect.height / 2

    const distance = Math.sqrt(
      Math.pow(mousePos.x - (charX - (containerRef.current?.getBoundingClientRect().left || 0)), 2) +
        Math.pow(mousePos.y - (charY - (containerRef.current?.getBoundingClientRect().top || 0)), 2),
    )

    const maxDistance = 300
    const proximity = Math.max(0, 1 - distance / maxDistance)

    const style: React.CSSProperties = {
      color: textColor,
      fontFamily,
      transition: "all 0.2s ease-out",
    }

    if (weight) {
      style.fontVariationSettings = `'wght' ${300 + proximity * 600}`
    }

    if (alpha) {
      style.opacity = 0.3 + proximity * 0.7
    }

    if (stroke) {
      style.WebkitTextStroke = `${proximity * 2}px ${strokeColor}`
      style.textStroke = `${proximity * 2}px ${strokeColor}`
    }

    return style
  }

  const chars = text.split("")
  const charRefs = useRef<(HTMLSpanElement | null)[]>([])

  return (
    <div ref={containerRef} className={`relative ${className}`} style={{ minHeight: minFontSize }}>
      <div className={flex ? "flex" : "inline"} style={{ justifyContent: "center" }}>
        {chars.map((char, index) => (
          <span
            key={index}
            ref={(el) => (charRefs.current[index] = el)}
            style={getCharStyle(index, charRefs.current[index])}
            className="inline-block"
          >
            {char === " " ? "\u00A0" : char}
          </span>
        ))}
      </div>
    </div>
  )
}
