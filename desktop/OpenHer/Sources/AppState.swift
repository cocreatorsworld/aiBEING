import SwiftUI
import Combine

/// App navigation phases
enum AppPhase: Equatable {
    case loading
    case discovery
    case awakening(Persona)
    case conversation
}

/// Global application state shared across all views.
@MainActor
final class AppState: ObservableObject {
    // MARK: - Navigation
    @Published var appPhase: AppPhase = .loading
    // MARK: - Connection
    @Published var isConnected: Bool = false
    @Published var serverURL: String = "http://localhost:8000"

    // MARK: - Personas
    @Published var personas: [Persona] = []
    @Published var selectedPersonaId: String?

    /// Toggle: only show personas that have a cabinet image ready.
    /// Persisted so the preference survives app restarts.
    @AppStorage("showOnlyReadyPersonas") var showOnlyReadyPersonas: Bool = true

    /// Personas filtered for display in DiscoveryView.
    /// When `showOnlyReadyPersonas` is on, only personas with a front.png are included.
    var displayPersonas: [Persona] {
        guard showOnlyReadyPersonas else { return personas }
        return personas.filter { $0.hasFront }
    }

    // MARK: - Chat
    @Published var messages: [ChatMessage] = []
    @Published var isTyping: Bool = false

    // MARK: - Message Merge Buffer
    /// Buffer for merging rapid consecutive messages before sending to backend.
    /// Messages flush when input loses focus or after hard cap timeout.
    private var _pendingTexts: [String] = []
    private var _mergeTask: Task<Void, Never>?
    private let _hardCapNanos: UInt64 = 15_000_000_000  // 15-second hard limit

    // MARK: - Mood (ambient system)
    @Published var currentMood: Mood = .calm
    @Published var valence: Double = 0.0       // Emotional valence EMA (-1...1)
    @Published var lastReward: Double = 0.0    // Reward per turn (-1...1), fluctuates each turn
    @Published var emotionTemperature: Double = 0.0  // Metabolic temperature (0...1)
    @Published var crystalCount: Int = 0       // Personal memory count

    // MARK: - Developer Mode
    /// Developer mode: shows EngineDebugPanel with neural network visualization.
    /// Persisted in UserDefaults so it survives app restarts.
    @Published var developerMode: Bool = false {
        didSet { UserDefaults.standard.set(developerMode, forKey: "developerMode") }
    }
    @Published var engineDebug: EngineDebugState = EngineDebugState()

    // MARK: - Demo Mode
    /// Persisted in UserDefaults so it survives app restarts.
    @Published var demoMode: Bool = false {
        didSet { UserDefaults.standard.set(demoMode, forKey: "demoMode") }
    }
    @Published var demoPresets: [DemoPreset] = []
    @Published var demoScenarios: [String: DemoScenario] = [:]
    @Published var demoSnapshot: DemoEngineSnapshot? = nil
    @Published var demoActMode: Int = 1  // 1=personas, 2=memory, 3=emotion, 4=time
    @Published var demoTitle: String = ""  // Large banner title set by demo scripts
    @Published var demoInjectedMemoryKeys: [String] = []  // Memory capsule keys to highlight

    // MARK: - Image Cache (shared between PersonaCard → AwakeningView)
    /// Front images cached after first download, keyed by personaId.
    var cachedFrontImages: [String: NSImage] = [:]

    // MARK: - Services
    lazy var apiClient: APIClient = APIClient(baseURL: self.serverURL)
    lazy var wsManager: WebSocketManager = WebSocketManager(appState: self)
    lazy var connectionManager: ConnectionManager = ConnectionManager(appState: self)

    var selectedPersona: Persona? {
        personas.first { $0.personaId == selectedPersonaId }
    }

    // MARK: - Init

    init() {
        // Read the saved URL before lazy services initialize
        let savedURL = UserDefaults.standard.string(forKey: "serverURL") ?? "http://localhost:8000"
        serverURL = savedURL
        // Restore persisted mode settings
        developerMode = UserDefaults.standard.bool(forKey: "developerMode")
        demoMode = UserDefaults.standard.bool(forKey: "demoMode")
        // In non-developer mode, attempt to restore the last conversation
        let savedPersonaId = UserDefaults.standard.string(forKey: "selectedPersonaId")

        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 300_000_000) // 0.3 seconds
            connectionManager.startMonitoring()
            await loadPersonas()

            if personas.isEmpty {
                // Backend is offline — load preview data
                loadPreviewData()
            }

            if developerMode {
                // Developer mode: always start in discovery
                appPhase = .discovery
            } else if let personaId = savedPersonaId,
               personas.contains(where: { $0.personaId == personaId }) {
                // Normal mode: restore the last conversation directly
                selectedPersonaId = personaId
                appPhase = .conversation
                await loadHistory(for: personaId)
                wsManager.connect()
            } else {
                // No saved persona: start in discovery

