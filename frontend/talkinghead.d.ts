// TalkingHead 套件沒有官方 TypeScript 型別定義,在此自行宣告
declare module "talkinghead" {
  export class TalkingHead {
    constructor(container: HTMLElement, options?: Record<string, unknown>);
    audioCtx: AudioContext;
    showAvatar(options: Record<string, unknown>): Promise<void>;
    speakAudio(
      audio: Record<string, unknown>,
      options?: Record<string, unknown>,
      onsubtitles?: (text: string) => void
    ): void;
    stop(): void;
  }
}