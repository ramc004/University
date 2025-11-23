import SwiftUI

struct HomeView: View {
    @State private var showLogoutPopup = false
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

            VStack(alignment: .center, spacing: 15) {
                HStack {
                    Button(action: { showLogoutPopup = true }) {
                        Image(systemName: "arrow.left")
                            .font(.system(size: 20, weight: .bold))
                    }
                    .buttonStyle(CircularIconButtonStyle(backgroundColor: .blue, foregroundColor: .white))

                    Spacer()

                    Button(action: {
                        // Handle add action here
                    }) {
                        Image(systemName: "plus")
                            .font(.system(size: 20, weight: .bold))
                    }
                    .buttonStyle(CircularIconButtonStyle(backgroundColor: .green, foregroundColor: .white))
                }
                .padding(.horizontal)
                .padding(.top, 30)

                Text("Home Automation")
                    .font(.largeTitle)
                    .bold()
                    .padding(.top, 20)

                Text("Welcome! You are successfully logged in.")
                    .font(.title2)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)

                Spacer()
            }
            .padding(.horizontal)

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

struct HomeView_Previews: PreviewProvider {
    static var previews: some View {
        HomeView()
    }
}
