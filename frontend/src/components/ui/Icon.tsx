export type IconName = 'home' | 'map' | 'folder' | 'file' | 'search' | 'upload' | 'github' | 'arrow' | 'layers' | 'spark' | 'code' | 'close' | 'chevron' | 'menu' | 'download'
const paths: Record<IconName, string> = {
  home: 'm3 10 9-7 9 7v11h-6v-7H9v7H3Z', map: 'M12 3v6M5 15v-3h14v3M3 15h4v5H3Zm7-12h4v5h-4Zm7 12h4v5h-4Z',
  folder: 'M3 5h6l2 3h10v12H3Z', file: 'M5 3h9l5 5v13H5Zm9 0v6h5M8 13h8M8 17h6',
  search: 'M21 21l-6-6M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0', upload: 'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',
  github: 'M9 19c-4 1-4-2-6-2m12 5v-4c0-1-.4-2-1-2 4-.4 6-2 6-6a5 5 0 0 0-1-3 5 5 0 0 0 0-4s-2 0-4 2a14 14 0 0 0-6 0C7 3 5 3 5 3a5 5 0 0 0 0 4 5 5 0 0 0-1 3c0 4 2 5.6 6 6-.6 0-1 1-1 2v4',
  arrow: 'M4 12h16m-6-6 6 6-6 6', layers: 'm12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5',
  spark: 'm12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z', code: 'm8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18',
  close: 'm5 5 14 14M19 5 5 19', chevron: 'm9 5 7 7-7 7', menu: 'M3 5h18M3 12h18M3 19h18', download: 'M12 3v13m-5-5 5 5 5-5M4 18v3h16v-3',
}
export function Icon({name, size = 18}: {name: IconName; size?: number}) { return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg> }
