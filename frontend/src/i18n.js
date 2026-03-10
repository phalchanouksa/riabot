import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    debug: true,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    resources: {
      en: {
        translation: {
          "language": "Language",
          "theme": "Theme",
          "light": "Light",
          "dark": "Dark",
          "english": "English",
          "khmer": "Khmer",
          "welcomeMessage": "Hi! I'm RiaBot. How can I help you with this new conversation?",
          "sessionRestarted": "Chat session restarted after 60 minutes of inactivity. Previous context lost.",
          "errorMessage": "Sorry, I'm having trouble responding. Please try again.",
          "resources": "Resources",
          "chatSessionExpired": {
            "title": "Chat Session Expired.",
            "body": "You're still logged in. Start a new chat or continue previous messages."
          },
          "newChat": "New Chat",
          "continue": "Continue",
          "howCanIHelp": "How can I help you today?",
          "riaBotIsThinking": "RiaBot is thinking...",
          "enterPrompt": "Write your message here", 
          "riaBotDisclaimer": "RiaBot can make mistakes. Check important info.",
          "editProfile": "Edit Profile",
          "logout": "Logout",
          "firstName": "First Name",
          "lastName": "Last Name",
          "enterFirstName": "Enter your first name",
          "enterLastName": "Enter your last name",
          "cancel": "Cancel",
          "save": "Save",
          "personalInfo": "Personal info",
          "security": "Security",
          "basicInfo": "Basic info",
          "basicInfoDesc": "Some info may be visible to other people using RiaBot services.",
          "email": "Email",
          "emailHint": "Contact support to change your email address",
          "changePassword": "Change password",
          "passwordDesc": "Use a strong password to keep your account secure.",
          "currentPassword": "Current password",
          "newPassword": "New password",
          "confirmPassword": "Confirm new password",
          "enterCurrentPassword": "Enter current password",
          "enterNewPassword": "Enter new password",
          "confirmNewPassword": "Confirm new password",
          "passwordMismatch": "Passwords do not match",
          "passwordTooShort": "Password must be at least 8 characters"
        }
      },
      km: {
        translation: {
          "language": "ភាសា",
          "theme": "ពណ៍",
          "light": "ភ្លឺ",
          "dark": "ងងឹត",
          "english": "អង់គ្លេស",
          "khmer": "ខ្មែរ",
          "welcomeMessage": "សួស្តី! ខ្ញុំគឺ RiaBot ។ តើខ្ញុំអាចជួយអ្នកក្នុងការសន្ទនាថ្មីនេះដោយរបៀបណា?",
          "sessionRestarted": "ការជជែកបានចាប់ផ្តើមឡើងវិញបន្ទាប់ពីអសកម្ម 60 នាទី​។",
          "errorMessage": "សូមអភ័យទោស ខ្ញុំមានបញ្ហាក្នុងការឆ្លើយតប។ សូម​ព្យាយាម​ម្តង​ទៀត។",
          "resources": "ធនធាន",
          "chatSessionExpired": {
            "title": "វគ្គជជែកបានផុតកំណត់ហើយ។",
            "body": "អ្នកនៅតែចូល។ ចាប់ផ្តើមការជជែកថ្មី ឬបន្តសារពីមុន។"
          },
          "newChat": "ចាប់ផ្តើមថ្មី",
          "continue": "បន្ត",
          "howCanIHelp": "តើខ្ញុំអាចជួយអ្នកដោយរបៀបណានៅថ្ងៃនេះ?",
          "riaBotIsThinking": "RiaBot កំពុងគិត...",
          "enterPrompt": "សរសេរសាររបស់អ្នកនៅទីនេះ", 
          "riaBotDisclaimer": "RiaBot អាចបង្ហាញព័ត៌មានមិនត្រឹមត្រូវ",
          "editProfile": "កែសម្រួលប្រវត្តិរូប",
          "logout": "ចាកចេញ",
          "firstName": "នាមខ្លួន",
          "lastName": "នាមត្រកូល",
          "enterFirstName": "បញ្ចូលនាមខ្លួនរបស់អ្នក",
          "enterLastName": "បញ្ចូលនាមត្រកូលរបស់អ្នក",
          "cancel": "បោះបង់",
          "save": "រក្សាទុក",
          "personalInfo": "ព័ត៌មានផ្ទាល់ខ្លួន",
          "security": "សុវត្ថិភាព",
          "basicInfo": "ព័ត៌មានមូលដ្ឋាន",
          "basicInfoDesc": "ព័ត៌មានមួយចំនួនអាចត្រូវបានមើលឃើញដោយអ្នកដទៃដែលប្រើសេវាកម្ម RiaBot។",
          "email": "អ៊ីមែល",
          "emailHint": "ទាក់ទងបុគ្គលិកជំនួយដើម្បីផ្លាស់ប្តូរអាសយដ្ឋានអ៊ីមែលរបស់អ្នក",
          "changePassword": "ផ្លាស់ប្តូរពាក្យសម្ងាត់",
          "passwordDesc": "ប្រើពាក្យសម្ងាត់ដ៏រឹងមាំដើម្បីរក្សាគណនីរបស់អ្នកឱ្យមានសុវត្ថិភាព។",
          "currentPassword": "ពាក្យសម្ងាត់បច្ចុប្បន្ន",
          "newPassword": "ពាក្យសម្ងាត់ថ្មី",
          "confirmPassword": "បញ្ជាក់ពាក្យសម្ងាត់ថ្មី",
          "enterCurrentPassword": "បញ្ចូលពាក្យសម្ងាត់បច្ចុប្បន្ន",
          "enterNewPassword": "បញ្ចូលពាក្យសម្ងាត់ថ្មី",
          "confirmNewPassword": "បញ្ជាក់ពាក្យសម្ងាត់ថ្មី",
          "passwordMismatch": "ពាក្យសម្ងាត់មិនត្រូវគ្នាទេ",
          "passwordTooShort": "ពាក្យសម្ងាត់ត្រូវតែមានយ៉ាងហោចណាស់ ៨ តួអក្សរ"
        }
      }
    }
  });

export default i18n;
