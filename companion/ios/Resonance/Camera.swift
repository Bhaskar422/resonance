@preconcurrency import AVFoundation
import UIKit

/// Records slow motion the way Resonance needs it: the back camera at its highest frame rate
/// (240 fps on recent iPhones), 1080p when possible, with focus and exposure locked so the
/// picture does not pump while it measures, plus audio for the diagnosis.
@MainActor
final class Camera: NSObject, ObservableObject {
    @Published var fps: Double = 0
    @Published var resolution = ""
    @Published var locked = false
    @Published var recording = false
    @Published var elapsed: Double = 0
    @Published var clip: URL?
    @Published var problem: String?

    let session = AVCaptureSession()
    private let output = AVCaptureMovieFileOutput()
    private var device: AVCaptureDevice?
    private var timer: Timer?
    private let queue = DispatchQueue(label: "resonance.camera")
    var duration: Double = 14

    func start() async {
        guard await AVCaptureDevice.requestAccess(for: .video) else {
            problem = "Allow camera access in Settings > Resonance."
            return
        }
        _ = await AVCaptureDevice.requestAccess(for: .audio)
        guard let cam = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            problem = "No back camera found."
            return
        }
        device = cam
        let session = self.session, output = self.output
        let chosen: (Double, String)? = await withCheckedContinuation { done in
            queue.async {
                session.beginConfiguration()
                if let input = try? AVCaptureDeviceInput(device: cam), session.canAddInput(input) { session.addInput(input) }
                if let mic = AVCaptureDevice.default(for: .audio), let input = try? AVCaptureDeviceInput(device: mic), session.canAddInput(input) { session.addInput(input) }
                if session.canAddOutput(output) { session.addOutput(output) }
                session.commitConfiguration()
                let result = Camera.useFastestFormat(cam)
                if let conn = output.connection(with: .video), conn.isVideoRotationAngleSupported(90) { conn.videoRotationAngle = 90 }
                session.startRunning()
                done.resume(returning: result)
            }
        }
        if let (rate, size) = chosen {
            fps = rate
            resolution = size
            if rate < 200 { problem = "This iPhone records at most \(Int(rate)) fps; vibration above \(Int(rate / 2)) Hz cannot be measured." }
        } else {
            problem = "Could not set up slow motion on this camera."
        }
    }

    /// The format with the highest frame rate, preferring 1920x1080 among equals.
    nonisolated private static func useFastestFormat(_ cam: AVCaptureDevice) -> (Double, String)? {
        func score(_ f: AVCaptureDevice.Format) -> (Double, Int) {
            let d = CMVideoFormatDescriptionGetDimensions(f.formatDescription)
            let rate = f.videoSupportedFrameRateRanges.map(\.maxFrameRate).max() ?? 0
            let sizeScore = d.width == 1920 && d.height == 1080 ? 3 : d.height >= 720 && d.height < 1080 ? 2 : d.height > 1080 ? 1 : 0
            return (rate, sizeScore)
        }
        guard let best = cam.formats.max(by: { score($0) < score($1) }) else { return nil }
        let rate = score(best).0
        do {
            try cam.lockForConfiguration()
            cam.activeFormat = best
            let frame = CMTime(value: 1, timescale: CMTimeScale(rate.rounded()))
            cam.activeVideoMinFrameDuration = frame
            cam.activeVideoMaxFrameDuration = frame
            cam.unlockForConfiguration()
        } catch {
            return nil
        }
        let d = CMVideoFormatDescriptionGetDimensions(best.formatDescription)
        return (rate, "\(d.width)x\(d.height)")
    }

    /// Focus and expose on the tapped spot, then hold them (the Camera app's AE/AF lock).
    func lock(at point: CGPoint) {
        guard let cam = device else { return }
        queue.async {
            guard (try? cam.lockForConfiguration()) != nil else { return }
            if cam.isFocusPointOfInterestSupported { cam.focusPointOfInterest = point }
            if cam.isFocusModeSupported(.autoFocus) { cam.focusMode = .autoFocus }
            if cam.isExposurePointOfInterestSupported { cam.exposurePointOfInterest = point }
            if cam.isExposureModeSupported(.autoExpose) { cam.exposureMode = .autoExpose }
            cam.unlockForConfiguration()
            Thread.sleep(forTimeInterval: 1.0)  // let them settle before freezing
            guard (try? cam.lockForConfiguration()) != nil else { return }
            if cam.isFocusModeSupported(.locked) { cam.focusMode = .locked }
            if cam.isExposureModeSupported(.locked) { cam.exposureMode = .locked }
            cam.unlockForConfiguration()
            Task { @MainActor in self.locked = true }
        }
    }

    func unlock() {
        guard let cam = device else { return }
        queue.async {
            guard (try? cam.lockForConfiguration()) != nil else { return }
            if cam.isFocusModeSupported(.continuousAutoFocus) { cam.focusMode = .continuousAutoFocus }
            if cam.isExposureModeSupported(.continuousAutoExposure) { cam.exposureMode = .continuousAutoExposure }
            cam.unlockForConfiguration()
            Task { @MainActor in self.locked = false }
        }
    }

    func record() {
        guard !recording else { return }
        let url = FileManager.default.temporaryDirectory.appending(path: "resonance-\(Int(Date().timeIntervalSince1970)).mov")
        clip = nil
        elapsed = 0
        recording = true
        output.startRecording(to: url, recordingDelegate: self)
        let started = Date()
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                self.elapsed = Date().timeIntervalSince(started)
                if self.elapsed >= self.duration { self.stop() }
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        if output.isRecording { output.stopRecording() }
    }
}

extension Camera: AVCaptureFileOutputRecordingDelegate {
    nonisolated func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo url: URL, from connections: [AVCaptureConnection], error: Error?) {
        Task { @MainActor in
            self.recording = false
            if let error, (error as NSError).userInfo[AVErrorRecordingSuccessfullyFinishedKey] as? Bool != true {
                self.problem = "Recording failed: \(error.localizedDescription)"
            } else {
                self.clip = url
            }
        }
    }
}
