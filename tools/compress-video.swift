// Re-encodes a video for the web with AVFoundation (no ffmpeg needed).
// usage: swift tools/compress-video.swift <in> <out.mp4> <width> <height> <bitrate>
// e.g.   swift tools/compress-video.swift raw.mp4 assets/video/smartrail.mp4 1080 720 1600000
import AVFoundation
import Foundation

let args = CommandLine.arguments
guard args.count == 6, let width = Int(args[3]), let height = Int(args[4]), let bitrate = Int(args[5]) else {
  print("usage: swift compress-video.swift <in> <out.mp4> <width> <height> <bitrate>")
  exit(1)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
try? FileManager.default.removeItem(at: outURL)

let asset = AVAsset(url: inURL)
let track = asset.tracks(withMediaType: .video)[0]
let reader = try AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
  kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange
])
reader.add(output)

let writer = try AVAssetWriter(outputURL: outURL, fileType: .mp4)
writer.shouldOptimizeForNetworkUse = true
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
  AVVideoCodecKey: AVVideoCodecType.h264,
  AVVideoWidthKey: width,
  AVVideoHeightKey: height,
  AVVideoScalingModeKey: AVVideoScalingModeResizeAspectFill,
  AVVideoCompressionPropertiesKey: [
    AVVideoAverageBitRateKey: bitrate,
    AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
    AVVideoMaxKeyFrameIntervalKey: 60,
  ],
])
input.transform = track.preferredTransform
input.expectsMediaDataInRealTime = false
writer.add(input)

reader.startReading()
writer.startWriting()
writer.startSession(atSourceTime: .zero)

let done = DispatchSemaphore(value: 0)
input.requestMediaDataWhenReady(on: DispatchQueue(label: "writer")) {
  while input.isReadyForMoreMediaData {
    if let buffer = output.copyNextSampleBuffer() {
      input.append(buffer)
    } else {
      input.markAsFinished()
      writer.finishWriting { done.signal() }
      return
    }
  }
}
done.wait()
print(writer.status == .completed ? "ok" : "failed: \(String(describing: writer.error))")
