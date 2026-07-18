# resume_utils.py — 履歷欄位共用工具
# Gemini 有時不會乖乖照 prompt 指示回傳純字串，而是回傳陣列或巢狀物件
# (例如技能給一串物件、經歷給多筆條目的 list)。若不處理，這些值會被
# 原封不動送到前端，controlled input 對非字串值呼叫內建 toString()，
# 陣列裡若是物件就會顯示成 "[object Object],[object Object]"。
# 這個函式把任何 JSON 值攤平成一段人類可讀的純文字，確保回傳給前端
# 與存入資料庫（欄位皆為 String）的一定是字串。

def flatten_resume_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        parts = [flatten_resume_value(v) for v in value.values()]
        return "、".join(p for p in parts if p)
    if isinstance(value, list):
        parts = [flatten_resume_value(item) for item in value]
        parts = [p for p in parts if p]
        # 條目本身是物件/巢狀結構（例如多筆經歷）時，用換行分段比較好讀；
        # 單純字串清單（例如技能列表）則用頓號連接。
        if any(isinstance(item, (dict, list)) for item in value):
            return "\n".join(parts)
        return "、".join(parts)
    return str(value)
