import { createContext, useContext, useReducer, type ReactNode } from 'react';
import { products } from '../data/mockData';
import type { DemoAction, DemoState } from '../types';
import { demoReducer } from './demoReducer';

const DemoContext = createContext<{ state: DemoState; dispatch: React.Dispatch<DemoAction> } | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(demoReducer, { products, cart: [] });
  return <DemoContext.Provider value={{ state, dispatch }}>{children}</DemoContext.Provider>;
}
export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error('useDemo must be used within DemoProvider');
  return value;
}
