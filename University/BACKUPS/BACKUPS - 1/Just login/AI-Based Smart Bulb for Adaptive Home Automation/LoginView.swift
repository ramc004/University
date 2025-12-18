import SwiftUI

struct LoginView: View {
  @State private var email = ""
  @State private var password = ""
  @State private var showPassword = false
  @State private var emailValid = true
  @State private var passwordValid = true
  @State private var errorMessage = ""
  @State private var loginMessage = ""
  @State private var loggingIn = false

  @State private var showResetPassword = false
  @State private var resetCode = ""
  @State private var navigateToHome = false

  var body: some View {
      ScrollView {
          VStack(alignment: .leading, spacing: 20) {
              Text("Login")
                  .font(.largeTitle)
                  .bold()

              VStack(alignment: .leading) {
                  Text("Email").font(.headline)
                  TextField("Enter your email", text: $email)
                      .textFieldStyle(RoundedBorderTextFieldStyle())
                      .autocapitalization(.none)
                      .keyboardType(.emailAddress)
                      .onChange(of: email) { _ in
                          emailValid = true
                          errorMessage = ""
                          loginMessage = ""
                      }
              }

              VStack(alignment: .leading) {
                  Text("Password").font(.headline)
                  HStack {
                      if showPassword {
                          TextField("Enter password", text: $password)
                      } else {
                          SecureField("Enter password", text: $password)
                      }
                      Button(action: { showPassword.toggle() }) {
                          Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill")
                              .foregroundColor(.gray)
                      }
                  }
                  .textFieldStyle(RoundedBorderTextFieldStyle())
                  .onChange(of: password) { _ in
                      passwordValid = true
                      errorMessage = ""
                  }
              }

              if !errorMessage.isEmpty {
                  Text(errorMessage).foregroundColor(.red).bold()
              }

              if !loginMessage.isEmpty {
                  Text(loginMessage).foregroundColor(.green).bold()
              }

              Button(action: loginUser) {
                  Text(loggingIn ? "Logging in..." : "Login").frame(maxWidth: .infinity)
              }
              .buttonStyle(ModernButtonStyle(backgroundColor: .blue))
              .disabled(loggingIn)
              .padding(.top, 20)

              Button(action: initiateForgotPassword) {
                  Text("Forgot Password?").foregroundColor(.red).underline()
              }
              .padding(.top, 10)

              NavigationLink("", destination: ResetPasswordView(email: email, verificationCode: resetCode, loginMessage: $loginMessage), isActive: $showResetPassword)
              NavigationLink("", destination: HomeView(), isActive: $navigateToHome)
          }
          .padding()
      }
      .navigationTitle("Login")
  }

  func loginUser() {
      loginMessage = ""
      errorMessage = ""

      if email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
          emailValid = false
          errorMessage = "Email cannot be empty."
          return
      }

      if password.isEmpty {
          passwordValid = false
          errorMessage = "Password cannot be empty."
          return
      }
      
      loggingIn = true

      guard let url = URL(string: "http://127.0.0.1:5000/login") else { return }
      var request = URLRequest(url: url)
      request.httpMethod = "POST"
      request.httpBody = try? JSONSerialization.data(withJSONObject: ["email": email, "password": password])
      request.setValue("application/json", forHTTPHeaderField: "Content-Type")

      URLSession.shared.dataTask(with: request) { data, response, error in
          DispatchQueue.main.async {
              loggingIn = false
              
              if let httpResponse = response as? HTTPURLResponse {
                  if httpResponse.statusCode == 200 {
                      // Store email locally for session management
                      UserDefaults.standard.set(email, forKey: "currentUserEmail")
                      UserDefaults.standard.set(true, forKey: "isLoggedIn")
                      navigateToHome = true
                  } else if let data = data,
                            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                            let message = json["message"] as? String {
                      if httpResponse.statusCode == 404 {
                          errorMessage = "This email has not been registered. Please register first."
                      } else if httpResponse.statusCode == 401 {
                          errorMessage = "Incorrect password. Please try again."
                      } else {
                          errorMessage = message
                      }
                  } else {
                      errorMessage = "Login failed. Please try again."
                  }
              } else {
                  errorMessage = "Network error. Please check your connection."
              }
          }
      }.resume()
  }

  func initiateForgotPassword() {
      if email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
          errorMessage = "Please enter your email address first."
          return
      }
      
      // First verify the email exists in the backend
      guard let url = URL(string: "http://127.0.0.1:5000/check_email") else { return }
      var request = URLRequest(url: url)
      request.httpMethod = "POST"
      request.httpBody = try? JSONSerialization.data(withJSONObject: ["email": email])
      request.setValue("application/json", forHTTPHeaderField: "Content-Type")

      URLSession.shared.dataTask(with: request) { data, _, error in
          DispatchQueue.main.async {
              if let data = data,
                 let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                 let available = json["available"] as? Bool {
                  
                  if available {
                      errorMessage = "This email is not registered."
                      return
                  }
                  
                  // Email exists, send reset code
                  resetCode = String(format: "%06d", Int.random(in: 0...999999))

                  guard let sendUrl = URL(string: "http://127.0.0.1:5000/send_code") else { return }
                  var sendRequest = URLRequest(url: sendUrl)
                  sendRequest.httpMethod = "POST"
                  sendRequest.httpBody = try? JSONSerialization.data(withJSONObject: ["email": email, "code": resetCode])
                  sendRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")

                  URLSession.shared.dataTask(with: sendRequest) { _, _, error in
                      DispatchQueue.main.async {
                          if let _ = error {
                              errorMessage = "Failed to send reset code. Please try again."
                          } else {
                              showResetPassword = true
                          }
                      }
                  }.resume()
              }
          }
      }.resume()
  }
}
