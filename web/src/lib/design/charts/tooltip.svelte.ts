// One tooltip per chart: ChartFrame provides it, marks call show()/hide(). Plain text content only (no HTML).
import { getContext, setContext } from 'svelte';

export interface TooltipContent {
  title: string;
  rows?: [string, string][];
  note?: string;
}

export class TooltipState {
  visible = $state(false);
  x = $state(0);
  y = $state(0);
  content = $state<TooltipContent | null>(null);
  host: HTMLElement | null = null;

  show(content: TooltipContent, ev: { clientX?: number; clientY?: number; currentTarget?: EventTarget | null }) {
    this.content = content;
    const box = this.host?.getBoundingClientRect();
    let cx = ev.clientX;
    let cy = ev.clientY;
    if ((cx === undefined || cy === undefined) && ev.currentTarget instanceof Element) {
      const r = ev.currentTarget.getBoundingClientRect();
      cx = r.left + r.width / 2;
      cy = r.top;
    }
    this.x = (cx ?? 0) - (box?.left ?? 0);
    this.y = (cy ?? 0) - (box?.top ?? 0);
    this.visible = true;
  }

  hide() {
    this.visible = false;
  }
}

const KEY = Symbol('chart-tooltip');

export function provideTooltip(): TooltipState {
  const t = new TooltipState();
  setContext(KEY, t);
  return t;
}

export function useTooltip(): TooltipState | undefined {
  return getContext<TooltipState | undefined>(KEY);
}
