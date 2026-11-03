import Foundation

/// The Resonance server's HTTP API, as the web app and the CLI use it (resonance/server.py).
struct Me: Codable { let id: String; let email: String; let name: String?; let admin: Int? }
struct TokenReply: Codable { let token: String; let user: Me }
struct DeviceStart: Codable { let device_code: String; let user_code: String; let verification_uri: String; let interval: Double?; let expires_in: Double? }
struct Job: Codable { let id: String; let status: String; let stage: String; let run: String?; let error: String?; let stages: [String] }
struct RunSummary: Codable, Identifiable, Hashable {
    let run: String; let created: Double; let machine: String?; let prompt: String?
    let freq_hz: Double; let fault: String?; let severity: String?; let mine: Bool?; let shared: Bool?
    var id: String { run }
}

struct APIError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

struct API {
    var server: URL
    var token: String?

    private func request(_ path: String, method: String = "GET", json: [String: String]? = nil) -> URLRequest {
        var r = URLRequest(url: server.appending(path: path))
        r.httpMethod = method
        if let token { r.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if let json {
            r.setValue("application/json", forHTTPHeaderField: "Content-Type")
            r.httpBody = try? JSONEncoder().encode(json)
        }
        return r
    }

    private func send<T: Decodable>(_ r: URLRequest, as: T.Type) async throws -> (T?, Int) {
        let (data, resp) = try await URLSession.shared.data(for: r)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        if code >= 400 {
            let detail = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String
            throw APIError(message: detail ?? "The server answered \(code).")
        }
        return (try? JSONDecoder().decode(T.self, from: data), code)
    }

    func signIn(email: String, password: String) async throws -> TokenReply {
        let r = request("api/auth/token", method: "POST", json: ["email": email, "password": password, "name": "Resonance iPhone app"])
        guard let reply = try await send(r, as: TokenReply.self).0 else { throw APIError(message: "Unexpected reply from the server.") }
        return reply
    }

    func startDeviceLogin() async throws -> DeviceStart {
        let r = request("api/cli/device", method: "POST", json: ["name": "Resonance iPhone app"])
        guard let d = try await send(r, as: DeviceStart.self).0 else { throw APIError(message: "Unexpected reply from the server.") }
        return d
    }

    /// The token once the code is approved on the website; nil while waiting.
    func pollDeviceLogin(_ deviceCode: String) async throws -> TokenReply? {
        let r = request("api/cli/poll", method: "POST", json: ["code": deviceCode])
        let (reply, code) = try await send(r, as: TokenReply.self)
        return code == 200 ? reply : nil
    }

    func me() async throws -> Me {
        guard let me = try await send(request("api/me"), as: Me.self).0 else { throw APIError(message: "Not signed in.") }
        return me
    }

    func runs() async throws -> [RunSummary] {
        try await send(request("api/runs"), as: [RunSummary].self).0 ?? []
    }

    func job(_ id: String) async throws -> Job {
        guard let j = try await send(request("api/jobs/\(id)"), as: Job.self).0 else { throw APIError(message: "Unknown job.") }
        return j
    }

    func reportURL(_ run: String) -> URL {
        URL(string: "\(server.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/")))/app#/runs/\(run)")!
    }

    /// Multipart upload to /api/analyze, streamed from a file so a 100 MB clip never sits in memory.
    func uploadRequest(video: URL, fields: [String: String]) throws -> (URLRequest, URL) {
        let boundary = "resonance-\(UUID().uuidString)"
        let body = FileManager.default.temporaryDirectory.appending(path: "upload-\(UUID().uuidString).multipart")
        FileManager.default.createFile(atPath: body.path, contents: nil)
        let out = try FileHandle(forWritingTo: body)
        defer { try? out.close() }
        func write(_ s: String) { out.write(s.data(using: .utf8)!) }
        for (k, v) in fields {
            write("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(k)\"\r\n\r\n\(v)\r\n")
        }
        write("--\(boundary)\r\nContent-Disposition: form-data; name=\"video\"; filename=\"\(video.lastPathComponent)\"\r\nContent-Type: video/quicktime\r\n\r\n")
        let input = try FileHandle(forReadingFrom: video)
        defer { try? input.close() }
        while let chunk = try input.read(upToCount: 4 << 20), !chunk.isEmpty { out.write(chunk) }
        write("\r\n--\(boundary)--\r\n")
        var r = request("api/analyze", method: "POST")
        r.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        r.timeoutInterval = 600
        return (r, body)
    }
}
