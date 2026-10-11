import { createContext, useContext, useReducer, useState, type ReactNode } from 'react';
import { products } from '../data/mockData';
import type { DemoAction, DemoState } from '../types';
import { demoReducer } from './demoReducer';

const DemoContext = createContext<{ state: DemoState; dispatch: React.Dispatch<DemoAction>; seller: string; setSeller: (seller: string) => void } | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(demoReducer, { products, cart: [], orders: [] });
  const [seller, setSeller] = useState('Mitti & Thread Studio');
  return <DemoContext.Provider value={{ state, dispatch, seller, setSeller }}>{children}</DemoContext.Provider>;
}
export function useDemo() {
  const value = useContext(DemoContext);
  if (!value) throw new Error('useDemo must be used within DemoProvider');
  return value;
}
