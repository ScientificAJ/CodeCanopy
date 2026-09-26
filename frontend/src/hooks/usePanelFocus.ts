import { useEffect } from 'react'
/** Keyboard focus stays in a modal drawer and returns to its opener on close. */
export function usePanelFocus(panel: 'navigation' | 'files' | 'context' | null, expanded: boolean) {
  useEffect(() => {
    const modal = expanded || (panel === 'files' ? innerWidth <= 650 : panel === 'context' ? innerWidth <= 1200 : panel === 'navigation' && innerWidth <= 900)
    if (!modal) return
    const selector = expanded ? '.source-expanded' : panel === 'files' ? '.tree-panel' : panel === 'context' ? '.context-panel' : '.nav-rail'
    const element = document.querySelector<HTMLElement>(selector)
    if (!element) return
    const opener = document.activeElement as HTMLElement | null
    const oldRole = element.getAttribute('role')
    element.setAttribute('role','dialog'); element.setAttribute('aria-modal','true')
    const available = () => [...element.querySelectorAll<HTMLElement>('button,a[href],input,select,summary,[tabindex="0"]')].filter(node => !node.hasAttribute('disabled') && node.getClientRects().length > 0)
    available()[0]?.focus()
    function trap(event: KeyboardEvent) {
      if (event.key !== 'Tab') return
      const items = available(); if (!items.length) return
      if (event.shiftKey && document.activeElement === items[0]) {event.preventDefault(); items.at(-1)?.focus()}
      else if (!event.shiftKey && document.activeElement === items.at(-1)) {event.preventDefault(); items[0]?.focus()}
    }
    element.addEventListener('keydown',trap)
    return () => {element.removeEventListener('keydown',trap); element.removeAttribute('aria-modal'); if(oldRole) element.setAttribute('role',oldRole); else element.removeAttribute('role'); opener?.focus()}
  }, [panel,expanded])
}
