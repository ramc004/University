struct APIConfig {
    // Toggle this for testing production
    static let useProduction = false
    
    static var baseURL: String {
#if targetEnvironment(simulator)
        return "http://127.0.0.1:5000"        // Local development
#else
#if DEBUG
        return "https://your-ngrok.ngrok-free.dev"  // ngrok (mobile data)
#else
        return "https://year-3-project.onrender.com" // Production
#endif
#endif
    }
}
