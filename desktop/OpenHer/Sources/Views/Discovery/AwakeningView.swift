import SwiftUI
import AVFoundation

/// Awakening transition — video → sci-fi initialization → conversation.
///
/// Transition strategy:
/// - The video remains visible as a background while the initialization sequence fades in on top.
/// - Initialization text is revealed character by character using a typewriter effect.
/// - Initialization text fades out before transitioning to the conversation.
struct AwakeningView: View {
    let persona: Persona
    @EnvironmentObject var appState: AppState

    // Video
    @State private var player: AVPlayer?
    @State private var hasVideo: Bool = false
    @State private var videoReady: Bool = false

    // Initialization sequence
    @State private var showInitSequence: Bool = false
    @State private var dimAmount: Double = 0
    @State private var initPhase: Int = 0
    @State private var typedTexts: [String] = []
    @State private var initComplete: Bool = false
    @State private var fadingOut: Bool = false

    // Name
    @State private var nameOpacity: Double = 0

    /// Persona-specific initialization steps
    private var initSteps: [String] {
        let mbti = persona.mbti ?? "UNKNOWN"
        let desc = persona.description ?? L10n.str("Standard Mode", en: "Standard")
        let tagStr = PersonaCard.localizedTags(persona).prefix(3).map { "#\($0)" }.joined(separator: " ")

        return [
            L10n.str("Initializing neural pathways...", en: "Initializing neural pathways..."),
            L10n.str("Loading memory data...", en: "Loading memory data..."),
            L10n.str("Setting personality: ", en: "Setting personality: ") + mbti,
            L10n.str("Calibrating emotion baseline: ", en: "Calibrating emotion baseline: ") + desc,
            L10n.str("Injecting resonance tags: ", en: "Injecting resonance tags: ") + tagStr,
            L10n.str("Booting consciousness core...", en: "Booting consciousness core..."),
        ]
    }

    var body: some View {
        ZStack {
            // === Layer 0: Base persona image (continuity from PersonaCard) ===
            personaBaseImage
                .ignoresSafeArea()

            // === Layer 1: Video — crossfades in slowly over the base image ===
            if hasVideo, let player = player {
                AVPlayerRepresentable(player: player)
                    .ignoresSafeArea()
                    .opacity(videoReady ? 1 : 0)
                    .animation(.easeInOut(duration: 0.8), value: videoReady)
            }

            // === Layer 2: Gradual dim overlay — bridges the video into initialization ===
            Paper.background
                .opacity(dimAmount)
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 1.2), value: dimAmount)

            // === Layer 3: Initialization sequence text ===
            if showInitSequence {
                initSequenceView
                    .opacity(fadingOut ? 0 : 1)
                    .animation(.easeOut(duration: 0.8), value: fadingOut)
            }
        }
        .onAppear {
            setupAwakening()
        }
        .onDisappear {
            cleanupPlayer()
        }
    }

    // MARK: - Base Image (loaded from backend API)

    @State private var baseNSImage: NSImage? = nil

    @ViewBuilder
    private var personaBaseImage: some View {
        if let nsImage = baseNSImage {
            GeometryReader { geo in
                Image(nsImage: nsImage)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .frame(width: geo.size.width, height: geo.size.height)
                    .clipped()
            }
        } else {
            Paper.background
        }
    }

    // MARK: - Initialization Sequence View

    private var initSequenceView: some View {
        VStack(spacing: 0) {
            Spacer()

            // Persona name
            Text(persona.displayName)
                .font(.system(size: 36, weight: .semibold, design: .serif))
                .foregroundStyle(Paper.herText)
                .opacity(nameOpacity)
                .padding(.bottom, 8)

            if let mbti = persona.mbti {
                Text(mbti)
                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                    .foregroundStyle(Paper.faint)
                    .opacity(nameOpacity)
                    .padding(.bottom, 36)
            }

            // Terminal log — typewriter style
            VStack(alignment: .leading, spacing: 12) {
                ForEach(0..<typedTexts.count, id: \.self) { i in
                    HStack(spacing: 10) {
                        // Checkmark for a completed line; spinner for the current line
                        if i < typedTexts.count - 1 || initComplete {
                            Image(systemName: "checkmark")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundStyle(Paper.coral)
                                .frame(width: 14, height: 14)
                        } else {
                            ProgressView()
                                .scaleEffect(0.45)
                                .frame(width: 14, height: 14)
                        }

                        Text(typedTexts[i])
                            .font(.system(size: 12, weight: .regular, design: .monospaced))
                            .foregroundStyle(Paper.ink.opacity(0.7))
                    }
                }
            }
            .frame(maxWidth: 300, alignment: .leading)

            Spacer().frame(height: 36)

            // Final ceremonial line
            if initComplete {
                Text(L10n.str("「\(persona.displayName) is online」", en: "「\(persona.displayName) is online」"))
                    .font(.system(size: 16, weight: .medium, design: .serif))
                    .foregroundStyle(Paper.coral)
                    .transition(.opacity)
            }

            Spacer()

            // Breathing dot
            Circle()
                .fill(Paper.coral)
                .frame(width: 6, height: 6)
                .scaleEffect(initPhase % 2 == 0 ? 1.0 : 1.4)
                .opacity(0.5)
                .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: initPhase)

            Spacer().frame(height: 40)
        }
        .padding(.horizontal, 40)
    }

    // MARK: - Setup

    private func setupAwakening() {
        let baseURL = appState.serverURL
        // Use the cached front image immediately (from PersonaCard) to prevent a white flash
        if let cached = appState.cachedFrontImages[persona.personaId] {
            self.baseNSImage = cached
        } else if persona.hasFront, let url = URL(string: "\(baseURL)/api/persona/\(persona.personaId)/media/front") {
            // Fallback: download if not in cache
            URLSession.shared.dataTask(with: url) { data, _, _ in
                if let data = data, let img = NSImage(data: data) {
                    DispatchQueue.main.async { self.baseNSImage = img }
                }
            }.resume()
        }

        // Load the awakening video from the backend API
        if persona.hasAwakeningVideo {
            let videoURLString = "\(appState.serverURL)/api/persona/\(persona.personaId)/media/awakening"
            if let videoURL = URL(string: videoURLString) {
                let asset = AVURLAsset(url: videoURL)
                let playerItem = AVPlayerItem(asset: asset)
                let avPlayer = AVPlayer(playerItem: playerItem)
                avPlayer.actionAtItemEnd = .pause  // Prevent looping

                self.player = avPlayer
                self.hasVideo = true

                // Start playback immediately
                avPlayer.play()

                // Crossfade the video in over the static PNG after a brief buffer
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                    videoReady = true
                }

                // Start the initialization sequence 2 seconds before the video ends
                Task {
                    let duration = try? await asset.load(.duration)
                    if let duration = duration {
                        let durationSec = CMTimeGetSeconds(duration)
                        let overlapStart = max(0, durationSec - 2.0)
                        let overlapTime = CMTime(seconds: overlapStart, preferredTimescale: 600)
                        avPlayer.addBoundaryTimeObserver(
                            forTimes: [NSValue(time: overlapTime)],
                            queue: .main
                        ) {
                            startInitSequence()
                        }
                    } else {
                        NotificationCenter.default.addObserver(
                            forName: .AVPlayerItemDidPlayToEndTime,
                            object: playerItem,
                            queue: .main
                        ) { _ in
                            self.startInitSequence()
                        }
                    }
                }
            }
        } else {
            // No video — begin initialization after a brief pause
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                startInitSequence()
            }
        }
    }

    // MARK: - Initialization Sequence with Typewriter

    private func startInitSequence() {
        guard !showInitSequence else { return }  // Prevent duplicate triggering
        showInitSequence = true

        // Gradually dim the video/background over 1.2 seconds
        dimAmount = 0.88_

