// A screen is a full-viewport layer owned by the UI stack (see index.ts).
export interface Screen {
  el: HTMLElement;
  /** Called just before the screen is shown (refresh dynamic content here). */
  onShow?(): void;
  /** Called when the screen is hidden or popped. */
  onHide?(): void;
  /** Esc / Android back. Return true when handled; otherwise the stack pops the screen. */
  back?(): boolean;
}

export const isCoarse = (): boolean => { try { return window.matchMedia('(pointer: coarse)').matches; } catch { return false; } };
