// Builds the 1200×630 social preview: dark brand background, hero scan image, logo.
// usage: swift tools/make-og-image.swift <hero.jpg> <logo-on-dark.svg> <out.jpg>
import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count == 4,
      let hero = NSImage(contentsOfFile: args[1]),
      let logo = NSImage(contentsOfFile: args[2]) else {
  print("usage: swift make-og-image.swift <hero.jpg> <logo.svg> <out.jpg>")
  exit(1)
}

let size = NSSize(width: 1200, height: 630)
let image = NSImage(size: size)
image.lockFocus()

// background #030712
NSColor(red: 3 / 255, green: 7 / 255, blue: 18 / 255, alpha: 1).setFill()
NSRect(origin: .zero, size: size).fill()

// soft cyan glow, top-left (brand cyan 600)
let glow = NSGradient(colors: [NSColor(red: 8 / 255, green: 145 / 255, blue: 178 / 255, alpha: 0.35),
                               NSColor(red: 3 / 255, green: 7 / 255, blue: 18 / 255, alpha: 0)])!
glow.draw(fromCenter: NSPoint(x: 0, y: size.height), radius: 0,
          toCenter: NSPoint(x: 0, y: size.height), radius: 700, options: [])

// hero scan on the right, black blends into the background (lighten)
let heroH: CGFloat = 560
let heroW = heroH * hero.size.width / hero.size.height
hero.draw(in: NSRect(x: size.width - heroW + 40, y: (size.height - heroH) / 2, width: heroW, height: heroH),
          from: .zero, operation: .lighten, fraction: 1)

// logo, left
let logoH: CGFloat = 64
let logoW = logoH * logo.size.width / logo.size.height
logo.draw(in: NSRect(x: 80, y: (size.height - logoH) / 2, width: logoW, height: logoH))

image.unlockFocus()

guard let tiff = image.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff) else { exit(1) }
// tiffRepresentation is at screen scale; force exact 1200×630 pixels
let out = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1200, pixelsHigh: 630, bitsPerSample: 8,
                           samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                           bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: out)
rep.draw(in: NSRect(x: 0, y: 0, width: 1200, height: 630))
NSGraphicsContext.restoreGraphicsState()
try! out.representation(using: .jpeg, properties: [.compressionFactor: 0.82])!.write(to: URL(fileURLWithPath: args[3]))
print("wrote", args[3])
