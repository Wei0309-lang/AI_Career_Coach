// 呼叫後端 API 的共用設定，各頁面與元件統一從這裡取用，避免各自重複定義
import { supabase } from "./supabaseClient";

export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// 每次呼叫受保護的後端 API 前，即時取用 Supabase session 的 JWT(後端一律以 JWT 驗證身份)。
// json=true 時加上 Content-Type;上傳檔案(FormData)時不要帶，瀏覽器會自動附上 multipart boundary
export async function authHeaders(json = false): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    throw new Error("尚未登入");
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${session.access_token}` };
  if (json) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

// 後端回傳的錯誤(detail 是給使用者看的中文訊息)，用來和網路斷線等其他錯誤區分
export class ApiError extends Error {}

// 後端失敗時回傳的 detail 已是給使用者看的中文訊息(例如 429「操作太頻繁，請約 N 秒後再試」)，
// 有的話就用它，沒有才用預設文字
export async function apiError(res: Response, fallback: string): Promise<ApiError> {
  const body = await res.json().catch(() => ({}));
  return new ApiError(typeof body.detail === "string" ? body.detail : fallback);
}
