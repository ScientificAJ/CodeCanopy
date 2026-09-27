// The hosted build ships a pixel-identical, lossless-compressed mascot.
export const brandLogo = import.meta.env.VITE_HOSTED === 'true' ? '/codecanopy-logo.webp' : '/codecanopy-logo.png'
