import SwiftUI

/// Settings — paper aesthetic, server URL config.
struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("serverURL") private var serverURL = "http://localhost:8000"

    var body: some View {
        Form {
            Section(L10n.str("Backend Server", en: "Backend Server")) {
                TextField("URL", text: $serverURL)
                    .textFieldStyle(.roundedBorder)

                Button(L10n.str("Save & Reconnect", en: "Save & Reconnect")) {
                    appState.updateServerURL(serverURL)
                }
                .foregroundStyle(Paper.coral)
            }

            Section(L10n.str("Display", en: "Display")) {
                Toggle(L10n.str("Show Ready Personas Only", en: "Show ready personas only"), isOn: $appState.showOnlyReadyPersonas)
                    .help(L10n.str("When enabled, only personas with an awakening cabinet image are shown", en: "When enabled, only personas with a cabinet image are shown"))
            }

            Section(L10n.str("Developer", en: "Developer")) {
                Toggle(L10n.str("Developer Mode", en: "Developer Mode"), isOn: $appState.developerMode)
                    .help(L10n.str("On startup, begin on the Discovery page and open the engine visualization window",
                                      en: "Start from Discovery on launch; open engine visualization"))
                    .onChange(of: appState.developerMode) { _, newValue in
                        if newValue {
                            NSApp.sendAction(Selector(("showEngineDebugWindow:")), to: nil, from: nil)
                        }
                    }

                if appState.developerMode {
                    Text(L10n.str("Open the visualization window via Window → Persona Engine",
                                  en: "Open via Window → Persona Engine menu"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .formStyle(.grouped)
        .frame(width: 360, height: 260)
    }
}
