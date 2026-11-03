import SwiftUI

struct RunsView: View {
    @EnvironmentObject var session: Session
    @Environment(\.openURL) private var openURL
    @State private var runs: [RunSummary] = []
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        NavigationStack {
            List {
                if let error { Text(error).foregroundStyle(.red) }
                if runs.isEmpty && !loading && error == nil {
                    Text("No runs yet. Record a clip and analyse it.").foregroundStyle(.secondary)
                }
                ForEach(runs) { r in
                    Button { if let api = session.api { openURL(api.reportURL(r.run)) } } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(r.machine ?? r.prompt?.capitalized ?? "Machine").font(.headline)
                                Spacer()
                                Text(String(format: "%.2f Hz", r.freq_hz)).font(.system(.subheadline, design: .monospaced))
                            }
                            HStack {
                                Text((r.fault ?? "not diagnosed").replacingOccurrences(of: "_", with: " ").capitalized)
                                if let s = r.severity { Text("· " + s.replacingOccurrences(of: "_", with: " ")).foregroundStyle(s == "normal" ? Theme.signal : Theme.warn) }
                                Spacer()
                                Text(Date(timeIntervalSince1970: r.created), style: .relative).foregroundStyle(.secondary)
                            }
                            .font(.caption)
                            if r.shared == true { Text("Shared example").font(.caption2).foregroundStyle(.secondary) }
                        }
                    }
                    .foregroundStyle(.primary)
                }
            }
            .navigationTitle("Runs")
            .refreshable { await load() }
            .task { await load() }
        }
    }

    private func load() async {
        guard let api = session.api else { return }
        loading = true
        do { runs = try await api.runs(); error = nil } catch { self.error = error.localizedDescription }
        loading = false
    }
}
