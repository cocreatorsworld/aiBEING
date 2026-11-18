import SwiftUI

/// Operator control panel for demo recording.
/// Clean and organized — controls only, with no state display (see DemoShowcasePanel).
/// ⌘D toggles visibility.
struct DemoBar: View {
    @EnvironmentObject var appState: AppState

    @State private var lastAction: String = ""
    @State private var actionOpacity: Double = 0

    private let personas: [(id: String, name: String, mbti: String)] = [
        ("luna",   "Luna",   "INFP"),
        ("vivian", "Vivian", "ENTJ"),
        ("kai",    "Kai",    "ISTP"),
    ]

    private let timeJumps: [(hours: Double, label: String)] = [
        (1, "+1h"), (4, "+4h"), (8, "+8h"), (24, "+24h"),
    ]

    private let scriptMessages: [(label: String, msg: String)] = [
        ("Project canceled", "My project was canceled today, and I'm in a bad mood"),
        ("Didn't sleep well", "I didn't sleep well today and feel exhausted"),
        ("Dango caused trouble", "Dango chewed through my headphone cable today"),
        ("Dango is adorable", "Yeah, it ran away super fast after chewing it. It's so cute"),
        ("Proposal rejected", "The proposal was rejected again"),
        ("A little annoyed", "I'm a little annoyed today"),
    ]

    private let memories: [(icon: String, label: String, content: String, category: String)] = [
        ("☕", "Black coffee", "The user likes Americano coffee with no sugar or milk", "preference"),
        ("🐱", "Cat named Dango", "The user has a three-year-old orange cat named Dango", "fact"),
        ("🏃", "Running hobby", "The user runs 5 kilometers every morning and is currently training for a marathon", "fact"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            divider
            personaSection
            divider
            timeSection
            divider
            testSection
            divider
            memorySection
        }
        .background(Paper.background)
        .onAppear {
            appState.demoMode = true
            appState.demoLoadPresets()
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: 8) {
            Text("DEMO")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(RoundedRectangle(cornerRadius: 5).fill(P](#)

