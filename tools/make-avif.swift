// Writes an AVIF copy next to each JPEG (same size) for <picture> sources.
// usage: swift tools/make-avif.swift assets/img/a.jpg [more.jpg ...]
import Foundation
import ImageIO

for path in CommandLine.arguments.dropFirst() {
  let url = URL(fileURLWithPath: path)
  guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
        let image = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    print("skip", path); continue
  }
  let out = url.deletingPathExtension().appendingPathExtension("avif")
  guard let dest = CGImageDestinationCreateWithURL(out as CFURL, "public.avif" as CFString, 1, nil) else {
    print("no AVIF encoder"); exit(1)
  }
  CGImageDestinationAddImage(dest, image, [kCGImageDestinationLossyCompressionQuality: 0.6] as CFDictionary)
  CGImageDestinationFinalize(dest)
  let before = (try? FileManager.default.attributesOfItem(atPath: path)[.size] as? Int) ?? 0
  let after = (try? FileManager.default.attributesOfItem(atPath: out.path)[.size] as? Int) ?? 0
  print("\(out.lastPathComponent): \(before / 1024) KB → \(after / 1024) KB")
}
