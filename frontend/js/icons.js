const glyphs={
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  coffee:'<path d="M10 2v2M14 2v2M6 8h12v8a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4z"/><path d="M18 10h1a3 3 0 1 1 0 6h-1M4 22h16"/>',
  about:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/>',
  gallery:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>',
  contact:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  bag:'<path d="M5 8h14l1 13H4L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.2 1.8c-1 .8-1.8 1.2-1.8 2.7M12 17h.01"/>',
  search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  arrowLeft:'<path d="M19 12H5m6-6-6 6 6 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  minus:'<path d="M5 12h14"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  close:'<path d="m18 6-12 12M6 6l12 12"/>',
  trash:'<path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/>',
  receipt:'<path d="M4 3h16v18l-3-2-3 2-2-2-3 2-2-2-3 2z"/><path d="M8 8h8M8 12h8M8 16h4"/>',
  leaf:'<path d="M20 4c-8 0-14 3-14 10a6 6 0 0 0 6 6c7 0 8-8 8-16Z"/><path d="M4 21c2-5 6-8 12-11"/>',
  sparkle:'<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3ZM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z"/>',
  location:'<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  hand:'<path d="M8 12V5a1.5 1.5 0 0 1 3 0v6-8a1.5 1.5 0 0 1 3 0v8-6a1.5 1.5 0 0 1 3 0v7-4a1.5 1.5 0 0 1 3 0v6c0 5-3 8-7 8h-1c-2 0-3.5-1-4.5-2.5L4 14a1.7 1.7 0 0 1 2.5-2.2L8 13"/>',
  thumbUp:'<path d="M7 10v11H4V10h3m3 11h6.5a2 2 0 0 0 1.9-1.4l2-6A2 2 0 0 0 18.5 11H14l.7-4.1A2 2 0 0 0 12.8 4L10 10v11z"/>',
  thumbDown:'<path d="M7 14V3H4v11h3m3-11h6.5a2 2 0 0 1 1.9 1.4l2 6A2 2 0 0 1 18.5 13H14l.7 4.1a2 2 0 0 1-1.9 2.9L10 14V3z"/>',
  camera:'<rect x="3" y="6" width="18" height="14" rx="2"/><circle cx="12" cy="13" r="3"/><path d="m8 6 1.5-2h5L16 6"/>'
};

export function icon(name,className=''){
  const paths=glyphs[name]||glyphs.sparkle;
  const extra=className?` ${className}`:'';
  return `<svg class="ui-icon${extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;
}
