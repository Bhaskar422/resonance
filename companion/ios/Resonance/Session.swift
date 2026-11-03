import Foundation
import Security

/// The signed-in account: server address (UserDefaults) and access token (Keychain).
@MainActor
final class Session: ObservableObject {
    @Published var server: String = UserDefaults.standard.string(forKey: "server") ?? "http://192.168.1.10:8000"
    @Published var token: String? = Keychain.read()
    @Published var me: Me?
    @Published var error: String?
    @Published var busy = false
    @Published var deviceCode: String?

    var api: API? {
        guard let url = URL(string: server.trimmingCharacters(in: .whitespaces)), url.scheme != nil else { return nil }
        return API(server: url, token: token)
    }

    func refresh() async {
        guard token != nil, let api else { return }
        do { me = try await api.me() } catch { signOut() }
    }

    func signIn(email: String, password: String) async {
        await run {
            guard let api = self.api else { throw APIError(message: "Enter the server address, e.g. http://192.168.1.10:8000") }
            self.keep(try await api.signIn(email: email, password: password))
        }
    }

    /// Sign in on the website (works for GitHub and Google accounts too), like `resonance login`.
    func signInWithBrowser(open: @escaping (URL) -> Void) async {
        await run {
            guard let api = self.api else { throw APIError(message: "Enter the server address first.") }
            let d = try await api.startDeviceLogin()
            self.deviceCode = d.user_code
            if let url = URL(string: d.verification_uri) { open(url) }
            let deadline = Date().addingTimeInterval(d.expires_in ?? 600)
            while Date() < deadline {
                try await Task.sleep(for: .seconds(d.interval ?? 2))
                if let reply = try await api.pollDeviceLogin(d.device_code) {
                    self.keep(reply)
                    self.deviceCode = nil
                    return
                }
            }
            self.deviceCode = nil
            throw APIError(message: "The code expired before it was approved. Try again.")
        }
    }

    func signOut() {
        Keychain.delete()
        token = nil
        me = nil
    }

    private func keep(_ reply: TokenReply) {
        UserDefaults.standard.set(server, forKey: "server")
        Keychain.save(reply.token)
        token = reply.token
        me = reply.user
    }

    private func run(_ work: @escaping () async throws -> Void) async {
        busy = true
        error = nil
        do { try await work() } catch { self.error = error.localizedDescription }
        busy = false
    }
}

enum Keychain {
    private static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "resonance", kSecAttrAccount as String: "token"]

    static func save(_ token: String) {
        delete()
        var q = query
        q[kSecValueData as String] = Data(token.utf8)
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(q as CFDictionary, nil)
    }

    static func read() -> String? {
        var q = query
        q[kSecReturnData as String] = true
        var out: AnyObject?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete() {
        SecItemDelete(query as CFDictionary)
    }
}
