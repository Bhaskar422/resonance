import SwiftUI

@main
struct ResonanceApp: App {
    @StateObject private var session = Session()

    var body: some Scene {
        WindowGroup {
            Group {
                if session.token == nil {
                    SignInView()
                } else {
                    TabView {
                        RecordView().tabItem { Label("Record", systemImage: "record.circle") }
                        RunsView().tabItem { Label("Runs", systemImage: "waveform.path.ecg") }
                        AccountView().tabItem { Label("Account", systemImage: "person.crop.circle") }
                    }
                }
            }
            .environmentObject(session)
            .tint(Theme.signal)
            .preferredColorScheme(.dark)
            .task { await session.refresh() }
        }
    }
}

enum Theme {
    static let signal = Color(red: 0.37, green: 0.94, blue: 0.63)  // the web app's --signal
    static let warn = Color(red: 0.96, green: 0.61, blue: 0.30)
}

struct SignInView: View {
    @EnvironmentObject var session: Session
    @Environment(\.openURL) private var openURL
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("http://192.168.1.10:8000", text: $session.server)
                        .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                } header: { Text("Server") } footer: {
                    Text("On your Mac run `resonance serve --host 0.0.0.0`, then enter its address on this Wi-Fi.")
                }
                Section("Email and password") {
                    TextField("you@example.com", text: $email)
                        .keyboardType(.emailAddress).textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField("Password", text: $password).textContentType(.password)
                    Button("Sign in") { Task { await session.signIn(email: email, password: password) } }
                        .disabled(session.busy || email.isEmpty || password.isEmpty)
                }
                Section {
                    Button("Sign in on the website") { Task { await session.signInWithBrowser { openURL($0) } } }
                        .disabled(session.busy)
                    if let code = session.deviceCode {
                        Text("Approve the code **\(code)** on the page that opened, then come back.")
                    }
                } footer: { Text("For accounts that use GitHub or Google, or to create a new account.") }
                if let e = session.error {
                    Section { Text(e).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Resonance")
        }
    }
}

struct AccountView: View {
    @EnvironmentObject var session: Session

    var body: some View {
        NavigationStack {
            Form {
                Section("Signed in") {
                    LabeledContent("Name", value: session.me?.name ?? "—")
                    LabeledContent("Email", value: session.me?.email ?? "—")
                    LabeledContent("Server", value: session.server)
                }
                Section {
                    Button("Sign out", role: .destructive) { session.signOut() }
                } footer: { Text("This forgets the token on this iPhone. Revoke it on the website in Settings > Access tokens.") }
            }
            .navigationTitle("Account")
        }
    }
}
