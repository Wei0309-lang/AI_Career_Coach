# avatar.py — 3D 虛擬人語音合成 Router
# 放在 repo 根目錄(與 Main.py 同層)
# 職責:接收面試官的文字回覆 → 呼叫 Azure Speech 產生
#       (1) zh-TW 語音 mp3  (2) viseme 嘴型時間軸
# 前端 TalkingHead 拿到這兩樣就能讓 3D 人物「開口說話」。
#
# 需要的環境變數(Render Dashboard 與本地 .env 都要加):
#   AZURE_SPEECH_KEY     Azure Speech 資源的金鑰(機密,不進 git)
#   AZURE_SPEECH_REGION  例如 eastasia(建議,離台灣最近)
#   AZURE_SPEECH_VOICE   選填,預設 zh-TW-YunJheNeural(男聲,符合嚴肅面試官人設)
#                         想換女聲可用 zh-TW-HsiaoChenNeural

import os
import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import azure.cognitiveservices.speech as speechsdk

router = APIRouter(prefix="/avatar", tags=["avatar"])


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
def synthesize_speech(req: TTSRequest):
    """把文字轉成語音(base64 mp3)+ viseme 嘴型時間軸。"""
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不可為空")
    # 防止過長文字燒掉免費額度(Azure F0 每月 50 萬字元)
    if len(text) > 1000:
        text = text[:1000]

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION", "eastasia")
    voice_name = os.getenv("AZURE_SPEECH_VOICE", "zh-TW-YunJheNeural")

    if not speech_key:
        raise HTTPException(
            status_code=500,
            detail="伺服器未設定 AZURE_SPEECH_KEY,請檢查環境變數",
        )

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=speech_region
    )
    speech_config.speech_synthesis_voice_name = voice_name
    # mp3 檔案小,適合 Render 免費方案的頻寬
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
    )

    # audio_config=None → 合成結果留在記憶體,不播放到伺服器音效裝置
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )

    # 收集 viseme 事件:Azure 會在每個「嘴型變化點」回呼一次
    # viseme_id: 0-21(Azure 定義的嘴型編號,前端會轉成 Oculus 格式)
    # audio_offset 單位是 tick(100 奈秒),除以 10000 轉成毫秒
    visemes: list[dict] = []

    def on_viseme(evt: speechsdk.SpeechSynthesisVisemeEventArgs):
        visemes.append(
            {
                "id": evt.viseme_id,
                "offset_ms": evt.audio_offset / 10000,
            }
        )

    synthesizer.viseme_received.connect(on_viseme)

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.Canceled:
        detail = result.cancellation_details
        raise HTTPException(
            status_code=502,
            detail=f"Azure 語音合成失敗: {detail.reason} {detail.error_details}",
        )
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise HTTPException(status_code=502, detail="Azure 語音合成未完成")

    return {
        "audio_base64": base64.b64encode(result.audio_data).decode("ascii"),
        "format": "mp3",
        "visemes": visemes,
    }
