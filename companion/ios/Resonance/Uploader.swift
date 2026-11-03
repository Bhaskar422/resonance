import Foundation

/// Sends a recorded clip to /api/analyze with upload progress, then follows the job's stages
/// until the report is ready.
@MainActor
final class Uploader: NSObject, ObservableObject, URLSessionTaskDelegate {
    @Published var sent: Double = 0  // 0...1
    @Published var stages: [String] = []
    @Published var status = ""  // "", uploading, running, done, error
    @Published var run: String?
    @Published var error: String?

    func upload(_ clip: URL, api: API, prompt: String, machine: String, diagnose: Bool, visualize: Bool) async {
        sent = 0; stages = []; run = nil; error = nil; status = "uploading"
        do {
            let fields = ["prompt": prompt, "machine": machine, "duration": "10", "diagnose": diagnose ? "true" : "false", "visualize": diagnose && visualize ? "true" : "false"]
            let (request, body) = try api.uploadRequest(video: clip, fields: fields)
            defer { try? FileManager.default.removeItem(at: body) }
            let (data, resp) = try await URLSession.shared.upload(for: request, fromFile: body, delegate: self)
            let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
            let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            guard code == 200, let job = obj?["job"] as? String else {
                throw APIError(message: (obj?["detail"] as? String) ?? "Upload failed (\(code)).")
            }
            status = "running"
            while true {
                let j = try await api.job(job)
                stages = j.stages
                if j.status == "done" { run = j.run; status = "done"; return }
                if j.status == "error" { throw APIError(message: j.error ?? "The analysis failed.") }
                try await Task.sleep(for: .seconds(1.5))
            }
        } catch {
            self.error = error.localizedDescription
            status = "error"
        }
    }

    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask, didSendBodyData bytesSent: Int64, totalBytesSent: Int64, totalBytesExpectedToSend: Int64) {
        let p = totalBytesExpectedToSend > 0 ? Double(totalBytesSent) / Double(totalBytesExpectedToSend) : 0
        Task { @MainActor in self.sent = p }
    }
}
