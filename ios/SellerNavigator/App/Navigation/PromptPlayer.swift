import AVFoundation

enum NavigationPrompt: String {
    case routeStarted = "route_started"
    case turnLeft = "turn_left"
    case turnRight = "turn_right"
    case continueStraight = "continue_straight"
    case offRoute = "off_route"
    case arrived
    case stopSkipped = "stop_skipped"
}

final class PromptPlayer {
    private var player: AVAudioPlayer?

    init() {
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? AVAudioSession.sharedInstance().setActive(true)
    }

    func play(_ prompt: NavigationPrompt) {
        guard let url = Bundle.main.url(forResource: prompt.rawValue, withExtension: "mp3") else { return }
        player = try? AVAudioPlayer(contentsOf: url)
        player?.prepareToPlay()
        player?.play()
    }
}
