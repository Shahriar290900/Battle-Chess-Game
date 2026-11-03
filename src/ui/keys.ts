// One table of keyboard shortcuts: the Controls page, the first-game card and every tooltip read it, so the keys
// shown to the player always match the ones that are wired.

export interface Shortcut { key: string; action: string; note: string }

export const KEY = {
  undo: 'U', moveList: 'M', back: 'Esc', freeLook: 'F', recenter: 'R', fallen: 'G', skip: 'Space', promote: '1-4',
} as const;

/** Keyboard rows of the Controls page. */
export const KEYBOARD: Shortcut[] = [
  { key: KEY.undo, action: 'Undo', note: 'Take back your last move (and the computer\'s reply)' },
  { key: KEY.moveList, action: 'Move list', note: 'Show or hide the journal of moves' },
  { key: KEY.back, action: 'Menu / back', note: 'Pause during a game; go back in menus' },
  { key: KEY.skip, action: 'Skip cinematic', note: 'Jump to the end of a fight animation (Enter works too)' },
  { key: KEY.promote, action: 'Promotion', note: '1 Queen, 2 Rook, 3 Bishop, 4 Knight' },
  { key: 'Arrows', action: 'Menu navigation', note: 'Move between buttons; Left and Right change a value' },
  { key: 'Enter', action: 'Choose', note: 'Activate the highlighted button' },
  { key: 'Q  E', action: 'Settings tabs', note: 'Previous or next settings category' },
];

/** Camera rows (keyboard, mouse and touch together). */
export const CAMERA: Array<[string, string]> = [
  [KEY.freeLook, 'Toggle the free orbit camera'],
  [KEY.recenter, 'Recenter: ease back to your seat'],
  [KEY.fallen, 'View fallen: fly to the captured pieces, press again for the other side'],
  ['Drag empty space', 'Look around (mouse)'],
  ['Wheel', 'Zoom (mouse)'],
  ['Two fingers', 'Look around; pinch to zoom (touch)'],
];

export const MOUSE: Array<[string, string]> = [
  ['Click', 'Select a piece, then click a lit tile to move'],
  ['Drag', 'Drag a piece onto a lit tile'],
  ['Click', 'Skip a fight animation'],
  ['Right-drag', 'Orbit the camera'],
  ['Wheel', 'Zoom'],
  ['Hover', 'Show a tooltip'],
];

export const TOUCH: Array<[string, string]> = [
  ['Tap', 'Select a piece, then tap a lit tile to move'],
  ['Drag', 'Optional: drag a piece to a tile'],
  ['Tap', 'Skip a fight animation'],
  ['Two-finger drag', 'Look around'],
  ['Pinch', 'Zoom'],
  ['Hold', 'Show a tooltip'],
];

/** True when the focus is in a text field: no shortcut may fire then. */
export function typing(target: EventTarget | null = document.activeElement): boolean {
  const el = target as HTMLElement | null;
  if (!el || el === document.body || typeof el.closest !== 'function') return false;
  return !!el.closest('input,textarea,select,[contenteditable=""],[contenteditable="true"]');
}
