import SwiftUI

struct HomeView: View {
    @State private var showLogoutPopup = false
    @State private var userBulbs: [SavedBulb] = []
    @State private var isLoadingBulbs = false
    @Environment(\.dismiss) var dismiss

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.95, green: 0.92, blue: 1.0),
                    Color(red: 0.98, green: 0.94, blue: 0.9),
                    Color(red: 0.9, green: 0.97, blue: 0.95)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 15) {
                // Header with buttons
                HStack {
                    Button(action: { showLogoutPopup = true }) {
                        Image(systemName: "arrow.left")
                            .font(.system(size: 20, weight: .bold))
                    }
                    .buttonStyle(CircularIconButtonStyle(backgroundColor: .blue, foregroundColor: .white))

                    Spacer()
                    
                    NavigationLink(destination: SettingsView()) {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 20, weight: .bold))
                    }
                    .buttonStyle(CircularIconButtonStyle(backgroundColor: .purple, foregroundColor: .white))

                    NavigationLink(destination: AddBulbView()) {
                        Image(systemName: "plus")
                            .font(.system(size: 20, weight: .bold))
                    }
                    .buttonStyle(CircularIconButtonStyle(backgroundColor: .green, foregroundColor: .white))
                }
                .padding(.horizontal)
                .padding(.top, 30)

                // Title and subtitle
                VStack(alignment: .leading, spacing: 8) {
                    Text("Home Automation")
                        .font(.largeTitle)
                        .bold()

                    // Show current mode
                    let simulatorMode = UserDefaults.standard.bool(forKey: "simulatorMode")
                    if UserDefaults.standard.object(forKey: "simulatorMode") == nil || simulatorMode {
                        HStack(spacing: 6) {
                            Image(systemName: "play.circle.fill")
                                .font(.caption)
                            Text("Simulator Mode Active")
                                .font(.caption)
                        }
                        .foregroundColor(.orange)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 4)
                        .background(Color.orange.opacity(0.1))
                        .cornerRadius(8)
                    } else {
                        Text("Welcome! Control your smart bulbs.")
                            .font(.title3)
                            .foregroundColor(.gray)
                    }
                }
                .padding(.horizontal)
                .padding(.top, 20)
                
                // Loading indicator or bulb list
                if isLoadingBulbs {
                    Spacer()
                    VStack(spacing: 15) {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("Loading your bulbs...")
                            .font(.subheadline)
                            .foregroundColor(.gray)
                    }
                    .frame(maxWidth: .infinity)
                    Spacer()
                } else if userBulbs.isEmpty {
                    Spacer()
                    VStack(spacing: 20) {
                        Image(systemName: "lightbulb.slash")
                            .font(.system(size: 60))
                            .foregroundColor(.gray)
                        
                        Text("No Bulbs Added Yet")
                            .font(.title2)
                            .bold()
                        
                        let simulatorMode = UserDefaults.standard.bool(forKey: "simulatorMode")
                        if UserDefaults.standard.object(forKey: "simulatorMode") == nil || simulatorMode {
                            Text("Tap the + button above to add simulated bulbs for testing")
                                .font(.subheadline)
                                .foregroundColor(.gray)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 40)
                        } else {
                            Text("Tap the + button above to add your first ESP32 smart bulb")
                                .font(.subheadline)
                                .foregroundColor(.gray)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 40)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    Spacer()
                } else {
                    // Bulb list
                    ScrollView {
                        VStack(spacing: 15) {
                            ForEach(userBulbs) { bulb in
                                NavigationLink(destination: SavedBulbControlView(savedBulb: bulb)) {
                                    SavedBulbRowView(bulb: bulb)
                                }
                                .buttonStyle(PlainButtonStyle())
                            }
                        }
                        .padding()
                    }
                }
            }

            // Logout confirmation popup
            if showLogoutPopup {
                ZStack {
                    Color.black.opacity(0.3).ignoresSafeArea()
                    VStack(spacing: 20) {
                        Text("Are you sure you want to log out?")
                            .font(.headline)
                            .multilineTextAlignment(.center)
                        HStack(spacing: 30) {
                            Button("No") { showLogoutPopup = false }
                                .buttonStyle(ModernButtonStyle(backgroundColor: .gray))
                            Button("Yes") {
                                showLogoutPopup = false
                                navigateToRootView()
                            }
                                .buttonStyle(ModernButtonStyle(backgroundColor: .red))
                        }
                    }
                    .padding()
                    .frame(width: 300)
                    .background(Color.white)
                    .cornerRadius(20)
                    .shadow(radius: 10)
                }
            }
        }
        .navigationBarHidden(true)
        .navigationBarBackButtonHidden(true)
        .onAppear {
            loadUserBulbs()
        }
        .refreshable {
            loadUserBulbs()
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("SimulatorModeChanged"))) { _ in
            print("🔄 Simulator mode changed, reloading bulbs...")
            loadUserBulbs()
        }
    }
    
    func loadUserBulbs() {
        guard let userEmail = UserDefaults.standard.string(forKey: "currentUserEmail") else {
            return
        }
        
        isLoadingBulbs = true
        
        // Get current simulator mode
        var simulatorMode = UserDefaults.standard.bool(forKey: "simulatorMode")
        if UserDefaults.standard.object(forKey: "simulatorMode") == nil {
            simulatorMode = true // Default to true if not set
            UserDefaults.standard.set(true, forKey: "simulatorMode")
        }
        
        print("📱 Loading bulbs - Simulator Mode: \(simulatorMode)")
        
        guard let url = URL(string: "\(APIConfig.baseURL)/get_bulbs") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        // Pass simulator_mode to backend to filter bulbs
        request.httpBody = try? JSONSerialization.data(withJSONObject: [
            "email": userEmail,
            "simulator_mode": simulatorMode
        ])
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoadingBulbs = false
                
                if let data = data,
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let bulbsData = json["bulbs"] as? [[String: Any]] {
                    
                    userBulbs = bulbsData.compactMap { dict in
                        guard let bulbId = dict["bulb_id"] as? String,
                              let bulbName = dict["bulb_name"] as? String else {
                            return nil
                        }
                        
                        let isSimulated = dict["is_simulated"] as? Bool ?? false
                        
                        print("  📦 Bulb: \(bulbName) - Simulated: \(isSimulated)")
                        
                        return SavedBulb(
                            bulb_id: bulbId,
                            bulb_name: bulbName,
                            room_name: dict["room_name"] as? String,
                            is_simulated: isSimulated
                        )
                    }
                    
                    let modeText = simulatorMode ? "SIMULATED" : "REAL"
                    print("✅ Loaded \(userBulbs.count) \(modeText) bulbs from database")
                }
            }
        }.resume()
    }
    
    func navigateToRootView() {
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let window = windowScene.windows.first else {
            return
        }
        
        window.rootViewController = UIHostingController(rootView: WelcomeView())
        window.makeKeyAndVisible()
        
        UIView.transition(with: window, duration: 0.3, options: .transitionCrossDissolve, animations: nil, completion: nil)
    }
}

// MARK: - Saved Bulb Model
struct SavedBulb: Identifiable {
    let id = UUID()
    let bulb_id: String
    let bulb_name: String
    let room_name: String?
    let is_simulated: Bool
}

// MARK: - Saved Bulb Row View
struct SavedBulbRowView: View {
    let bulb: SavedBulb
    
    var body: some View {
        HStack(spacing: 15) {
            // Bulb Icon
            ZStack {
                Image(systemName: "lightbulb.fill")
                    .font(.system(size: 30))
                    .foregroundColor(.yellow)
                    .frame(width: 50, height: 50)
                    .background(Color.gray.opacity(0.1))
                    .clipShape(Circle())
                
                // Simulated indicator
                if bulb.is_simulated {
                    Circle()
                        .fill(Color.orange)
                        .frame(width: 14, height: 14)
                        .overlay(
                            Image(systemName: "play.fill")
                                .font(.system(size: 6))
                                .foregroundColor(.white)
                        )
                        .offset(x: 18, y: -18)
                }
            }
            
            // Bulb Info
            VStack(alignment: .leading, spacing: 5) {
                Text(bulb.bulb_name)
                    .font(.headline)
                    .foregroundColor(.primary)
                
                if let room = bulb.room_name, !room.isEmpty {
                    Text(room)
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                
                if bulb.is_simulated {
                    HStack(spacing: 4) {
                        Image(systemName: "play.circle.fill")
                            .font(.system(size: 8))
                        Text("Simulated")
                            .font(.system(size: 10))
                    }
                    .foregroundColor(.orange)
                }
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .foregroundColor(.gray)
        }
        .padding()
        .background(Color.white.opacity(0.8))
        .cornerRadius(15)
        .shadow(color: Color.black.opacity(0.1), radius: 5, x: 0, y: 2)
    }
}

struct HomeView_Previews: PreviewProvider {
    static var previews: some View {
        HomeView()
    }
}
