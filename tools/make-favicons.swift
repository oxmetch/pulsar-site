// Centers an image on a transparent square canvas and writes PNG favicons.
// usage: swift tools/make-favicons.swift <source.png> <outDir>
import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count == 3, let source = NSImage(contentsOfFile: args[1]),
      let cg = source.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
  print("usage: swift make-favicons.swift <source.png> <outDir>")
  exit(1)
}
let outDir = URL(fileURLWithPath: args[2])

// name: (size, padding as share of the canvas)
let targets: [(String, Int, Double)] = [
  ("favicon-32.png", 32, 0.0),
  ("favicon-48.png", 48, 0.0),
  ("apple-touch-icon.png", 180, 0.0),
  ("icon-192.png", 192, 0.0),
  ("icon-512.png", 512, 0.0),
]

for (name, size, pad) in targets {
  let ctx = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpaceCreateDeviceRGB(),
                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.interpolationQuality = .high
  let box = Double(size) * (1 - pad * 2)
  let scale = min(box / Double(cg.width), box / Double(cg.height))
  let w = Double(cg.width) * scale, h = Double(cg.height) * scale
  ctx.draw(cg, in: CGRect(x: (Double(size) - w) / 2, y: (Double(size) - h) / 2, width: w, height: h))
  let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
  try rep.representation(using: .png, properties: [:])!.write(to: outDir.appendingPathComponent(name))
  print("wrote", name)
}
