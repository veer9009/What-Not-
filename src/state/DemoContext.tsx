import { createContext, useContext, useReducer, useState, type ReactNode } from 'react';
import { products } from '../data/mockData';
import type { DemoAction, DemoState } from '../types';
import { demoReducer } from './demoReducer';
import { loadAttempts } from './checkoutRecovery';

const DemoContext = createContext<{ state: DemoState; dispatch: React.Dispatch<DemoAction>; seller: string; setSeller: (seller: string) => void } | null>(null);
export function DemoProvider({ children, ownerId }: { children: ReactNode; ownerId?: string }) {
  const [state, dispatch] = useReducer(demoReducer, ownerId,
    buyerId=>({ products, cart: [], orders: [], placements: loadAttempts(buyerId) }));
  const [seller, setSeller] = useState('Mitti & Thread Studio');
  return <DemoContext.Provider value={{ state, dispatch, seller, setSeller }}>{children}</DemoContext.Provider>;
}
export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error('useDemo must be used within DemoProvider');
  return value;
}
