import { Logo } from './Shared';
import city from '../assets/login/city.webp';
import town from '../assets/login/town.webp';
import village from '../assets/login/village.webp';
import neighborhood480 from '../assets/homepage/neighborhood-world-480.webp';
import neighborhood768 from '../assets/homepage/neighborhood-world-768.webp';
import neighborhood976 from '../assets/homepage/neighborhood-world-976.webp';
import neighborhoodFallback from '../assets/homepage/neighborhood-world.jpg';

/** Shared public authentication presentation. No role, location or authentication state. */
export function LoginDiscoveryPanel() {
  return <aside className="login-aside login-discovery-panel" aria-labelledby="login-discovery-title">
    <Logo light/>
    <div className="login-discovery-copy">
      <h1 id="login-discovery-title">Local possibilities, wherever you live.</h1>
      <p>Discover nearby sellers, properties, and services where local listings are available.</p>
    </div>
    <div className="login-discovery-art" data-testid="login-discovery-art" aria-hidden="true">
        <div className="login-community-scenes">
          {([{label:'City',src:city,height:120},{label:'Town',src:town,height:120},{label:'Village',src:village,height:104}]).map(scene=><figure key={scene.label}><img src={scene.src} width={350} height={scene.height} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer"/><figcaption>{scene.label}</figcaption></figure>)}
        </div>
      <picture className="login-neighborhood"><source type="image/webp" srcSet={`${neighborhood480} 480w, ${neighborhood768} 768w, ${neighborhood976} 976w`} sizes="(max-width: 700px) 1px, (max-width: 1100px) 44vw, 600px"/><img src={neighborhoodFallback} width={976} height={596} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer"/></picture>
    </div>
    <p className="login-discovery-note">Illustration only. Local listings and beta access depend on availability.</p>
  </aside>;
}
