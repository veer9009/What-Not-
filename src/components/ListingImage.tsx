import { ImageOff } from 'lucide-react';
import { useState } from 'react';

/** Presentation only: never substitutes a demo photo for a real listing. */
export function ListingImage({ src, alt }: { src?: string | null; alt: string }) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  if (!src || failedSource === src) {
    return <div className="listing-image-placeholder" role="img" aria-label={`${alt}: image unavailable`}><ImageOff size={28} aria-hidden="true"/><span>No photo yet</span></div>;
  }
  return <img src={src} alt={alt} referrerPolicy="no-referrer" onError={() => setFailedSource(src)}/>;
}
