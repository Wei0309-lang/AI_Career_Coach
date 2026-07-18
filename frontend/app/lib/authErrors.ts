// 將 Supabase Auth 回傳的英文錯誤訊息轉成中文提示，AuthPage 與 reset-password 頁面共用
export function translateAuthError(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("already registered") || lower.includes("already exists")) {
    return "此 Email 已被註冊，請直接登入或使用忘記密碼功能。";
  }
  if (lower.includes("invalid login credentials")) {
    return "帳號或密碼錯誤。";
  }
  if (lower.includes("email not confirmed")) {
    return "此帳號尚未完成信件驗證，請先至信箱點擊驗證連結。";
  }
  if (lower.includes("password") && (lower.includes("least") || lower.includes("short") || lower.includes("weak"))) {
    return "密碼強度不足，請至少輸入 6 個字元。";
  }
  if (lower.includes("rate limit") || lower.includes("too many") || lower.includes("after")) {
    return "操作過於頻繁，請稍後再試一次。";
  }
  if (lower.includes("unable to validate email") || lower.includes("invalid email")) {
    return "Email 格式不正確，請重新確認。";
  }
  return message;
}
