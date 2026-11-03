@preconcurrency import AVFoundation
import SwiftUI

struct RecordView: View {
    @EnvironmentObject var session: Session
    @StateObject private var camera = Camera()

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                CameraPreview(session: camera.session) { camera.lock(at: $0) }
                    .ignoresSafeArea(edges: .top)
                VStack {
                    HStack(spacing: 8) {
                        Badge(text: camera.fps > 0 ? "\(Int(camera.fps)) FPS" : "…", color: camera.fps >= 200 ? Theme.signal : Theme.warn)
                        if !camera.resolution.isEmpty { Badge(text: camera.resolution, color: .white.opacity(0.8)) }
                        Spacer()
                        Button { camera.locked ? camera.unlock() : camera.lock(at: CGPoint(x: 0.5, y: 0.5)) } label: {
                            Badge(text: camera.locked ? "AE/AF LOCK" : "TAP TO LOCK", color: camera.locked ? Theme.warn : .white.opacity(0.8))
                        }
                    }
                    .padding()
                    if let p = camera.problem {
                        Text(p).font(.footnote).padding(10).background(.black.opacity(0.7)).clipShape(RoundedRectangle(cornerRadius: 8)).padding(.horizontal)
                    }
                    Spacer()
                    if camera.recording {
                        Text(String(format: "%.1f / %.0f s", camera.elapsed, camera.duration))
                            .font(.system(.title3, design: .monospaced).weight(.semibold))
                            .padding(.bottom, 8)
                    } else {
                        Text("Hold still on a tripod · machine fills a third of the frame · tap it to lock")
                            .font(.caption).multilineTextAlignment(.center).foregroundStyle(.white.opacity(0.8)).padding(.horizontal, 30)
                    }
                    Button { camera.recording ? camera.stop() : camera.record() } label: {
                        ZStack {
                            Circle().stroke(.white, lineWidth: 4).frame(width: 76, height: 76)
                            RoundedRectangle(cornerRadius: camera.recording ? 6 : 32).fill(.red)
                                .frame(width: camera.recording ? 30 : 62, height: camera.recording ? 30 : 62)
                        }
                    }
                    .accessibilityLabel(camera.recording ? "Stop recording" : "Record 14 seconds")
                    .padding(.bottom, 24)
                }
            }
            .navigationTitle("Record")
            .navigationBarTitleDisplayMode(.inline)
            .task { await camera.start() }
            .sheet(item: Binding(get: { camera.clip.map(Clip.init) }, set: { if $0 == nil { camera.clip = nil } })) { clip in
                SendView(clip: clip.url)
            }
        }
    }
}

struct Clip: Identifiable { let url: URL; var id: URL { url } }

struct Badge: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text).font(.system(size: 12, weight: .semibold, design: .monospaced)).foregroundStyle(color)
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(.black.opacity(0.55)).clipShape(RoundedRectangle(cornerRadius: 4))
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(color.opacity(0.6)))
    }
}

/// What the clip shows, then upload it for analysis in this account.
struct SendView: View {
    let clip: URL
    @EnvironmentObject var session: Session
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @StateObject private var up = Uploader()
    @AppStorage("prompt") private var prompt = "fan"
    @AppStorage("machine") private var machine = ""
    @AppStorage("diagnose") private var diagnose = true
    @AppStorage("visualize") private var visualize = true
    @State private var measured = ""

    private let order = ["upload", "prepare", "mask", "measure", "accel", "magnify", "plot", "diagnose", "visualize"]

    var body: some View {
        NavigationStack {
            Form {
                Section("Clip") {
                    LabeledContent("Recorded", value: measured.isEmpty ? "…" : measured)
                }
                Section {
                    TextField("fan, pump, motor", text: $prompt).textInputAutocapitalization(.never)
                    TextField("Machine name, e.g. NUUK LIT v2 table fan", text: $machine)
                } header: { Text("What to measure") } footer: { Text("One or two words SAM 3.1 can find in the picture. Use the same machine name every time so its runs are grouped.") }
                Section {
                    Toggle("Diagnose with Muse Spark", isOn: $diagnose)
                    Toggle("Show the fix with Muse Image", isOn: $visualize).disabled(!diagnose)
                }
                if up.status != "" {
                    Section("Progress") {
                        if up.status == "uploading" { ProgressView(value: up.sent) { Text("Uploading \(Int(up.sent * 100)) %") } }
                        ForEach(order.filter { up.stages.contains($0) }, id: \.self) { s in
                            Label(s.capitalized, systemImage: "checkmark.circle.fill").foregroundStyle(Theme.signal)
                        }
                        if up.status == "running" { ProgressView().frame(maxWidth: .infinity) }
                        if let e = up.error { Text(e).foregroundStyle(.red) }
                    }
                }
                Section {
                    if let run = up.run, let api = session.api {
                        Button("Open the report") { openURL(api.reportURL(run)) }
                    } else {
                        Button("Analyse") {
                            guard let api = session.api else { return }
                            Task { await up.upload(clip, api: api, prompt: prompt, machine: machine, diagnose: diagnose, visualize: visualize) }
                        }
                        .disabled(prompt.isEmpty || up.status == "uploading" || up.status == "running")
                    }
                }
            }
            .navigationTitle("Analyse clip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .task { measured = await describe(clip) }
        }
    }

    /// Frame rate and length as stored in the file, so a bad clip is caught before upload.
    private func describe(_ url: URL) async -> String {
        let asset = AVURLAsset(url: url)
        guard let track = try? await asset.loadTracks(withMediaType: .video).first,
              let rate = try? await track.load(.nominalFrameRate),
              let length = try? await asset.load(.duration) else { return "unknown" }
        return String(format: "%.0f fps · %.1f s", rate, CMTimeGetSeconds(length))
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    let onTap: (CGPoint) -> Void

    func makeUIView(context: Context) -> PreviewView {
        let v = PreviewView()
        v.layer.session = session
        v.layer.videoGravity = .resizeAspect
        if let conn = v.layer.connection, conn.isVideoRotationAngleSupported(90) { conn.videoRotationAngle = 90 }
        v.onTap = onTap
        return v
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {}

    final class PreviewView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        override var layer: AVCaptureVideoPreviewLayer { super.layer as! AVCaptureVideoPreviewLayer }
        var onTap: ((CGPoint) -> Void)?

        override init(frame: CGRect) {
            super.init(frame: frame)
            addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(tapped(_:))))
        }

        required init?(coder: NSCoder) { fatalError("not used") }

        @objc private func tapped(_ g: UITapGestureRecognizer) {
            onTap?(layer.captureDevicePointConverted(fromLayerPoint: g.location(in: self)))
        }
    }
}
