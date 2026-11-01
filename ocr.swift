import Foundation
import Vision
import AppKit

// usage: ocr image.png  -> lines "x y w h<TAB>text" in image pixels (top-left origin)
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let W = Double(cg.width), H = Double(cg.height)
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cg).perform([req])
for o in req.results ?? [] {
    guard let t = o.topCandidates(1).first else { continue }
    let b = o.boundingBox
    print(String(format: "%.0f %.0f %.0f %.0f\t", b.minX * W, (1 - b.maxY) * H, b.width * W, b.height * H) + t.string)
}
