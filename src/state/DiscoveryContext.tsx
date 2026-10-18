import { createContext, useContext, useState, type ReactNode } from 'react';
import type { DiscoverySource } from '../api/discovery';

interface State {source:DiscoverySource|null;choose:(source:DiscoverySource|null)=>void}
const Context=createContext<State|null>(null);
export function DiscoveryProvider({children}:{children:ReactNode}){
  const [source,choose]=useState<DiscoverySource|null>(null);
  return <Context.Provider value={{source,choose}}>{children}</Context.Provider>;
}
export function useDiscovery(){const state=useContext(Context);if(!state)throw new Error('DiscoveryProvider is required');return state;}
