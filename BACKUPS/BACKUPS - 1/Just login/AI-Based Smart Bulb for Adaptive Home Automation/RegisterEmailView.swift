import SwiftUI

struct RegisterEmailView: View {
   @State private var email = ""
   @State private var usernameValid = false
   @State private var atSignValid = false
   @State private var domainValid = false
   @State private var emailAvailable = false
   @State private var showPasswordView = false
   @State private var sendingCode = false
   @State private var checkingEmail = false
   @State private var errorMessage = ""
   @State private var verificationCode = ""

   var body: some View {
       ScrollView {
           VStack(alignment: .leading, spacing: 20) {
               Text("Register Account").font(.largeTitle).bold()

               VStack(alignment: .leading) {
                   Text("Email Address").font(.headline)
                   TextField("Enter your email", text: $email)
                       .textFieldStyle(RoundedBorderTextFieldStyle())
                       .autocapitalization(.none)
                       .keyboardType(.emailAddress)
                       .onChange(of: email) { _ in validateEmail() }
               }

               VStack(alignment: .leading, spacing: 6) {
                   Text("Email Validation:").font(.subheadline).bold()
                   Text(usernameValid ? "✅ Username before @ is valid" : "❌ Enter username before @")
                   Text(atSignValid ? "✅ Contains @" : "❌ Missing @")
                   Text(domainValid ? "✅ Domain is valid" : "❌ Invalid domain (e.g., example.com)")
                   
                   if checkingEmail {
                       Text("⏳ Checking availability...")
                   } else if email.isEmpty || !atSignValid || !domainValid {
                       Text("❌ Email availability unchecked")
                   } else {
                       Text(emailAvailable ? "✅ Email available" : "❌ Email already registered")
                   }
               }
               .foregroundColor(.gray)

               Button(action: sendVerificationCode) {
                   Text(sendingCode ? "Sending..." : "Verify Email").frame(maxWidth: .infinity)
               }
               .buttonStyle(ModernButtonStyle(backgroundColor: .green))
               .disabled(!allEmailRulesValid() || sendingCode || checkingEmail)
               .padding(.top, 10)

               if !errorMessage.isEmpty {
                   Text(errorMessage).foregroundColor(.red).bold()
               }

               NavigationLink("", destination: RegisterPasswordView(email: email, verificationCode: verificationCode), isActive: $showPasswordView)
           }
           .padding()
       }
       .navigationTitle("Step 1: Email")
   }

   func validateEmail() {
       let parts = email.split(separator: "@")
       usernameValid = (parts.first?.isEmpty == false)
       atSignValid = email.contains("@")
       domainValid = parts.count == 2 && parts[1].contains(".")
       
       // Check email availability with backend
       if usernameValid && atSignValid && domainValid {
           checkEmailAvailability()
       } else {
           emailAvailable = false
       }
   }
   
   func checkEmailAvailability() {
       checkingEmail = true
       guard let url = URL(string: "http://127.0.0.1:5000/check_email") else { return }
       var request = URLRequest(url: url)
       request.httpMethod = "POST"
       request.httpBody = try? JSONSerialization.data(withJSONObject: ["email": email])
       request.setValue("application/json", forHTTPHeaderField: "Content-Type")

       URLSession.shared.dataTask(with: request) { data, _, error in
           DispatchQueue.main.async {
               checkingEmail = false
               if let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let available = json["available"] as? Bool {
                   emailAvailable = available
               } else {
                   emailAvailable = false
               }
           }
       }.resume()
   }

   func allEmailRulesValid() -> Bool {
       return usernameValid && atSignValid && domainValid && emailAvailable
   }

   func sendVerificationCode() {
       guard allEmailRulesValid() else {
           errorMessage = "Fix email before continuing"
           return
       }

       sendingCode = true
       errorMessage = ""
       verificationCode = String(format: "%06d", Int.random(in: 0...999999)).trimmingCharacters(in: .whitespacesAndNewlines)

       guard let url = URL(string: "http://127.0.0.1:5000/send_code") else { return }
       var request = URLRequest(url: url)
       request.httpMethod = "POST"
       request.httpBody = try? JSONSerialization.data(withJSONObject: ["email": email, "code": verificationCode])
       request.setValue("application/json", forHTTPHeaderField: "Content-Type")

       URLSession.shared.dataTask(with: request) { _, _, error in
           DispatchQueue.main.async {
               sendingCode = false
               if error != nil {
                   errorMessage = "Failed to send email"
               } else {
                   showPasswordView = true
               }
           }
       }.resume()
   }
}
