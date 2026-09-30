import type { DemoAction, DemoState } from '../types';

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case 'cart/add': {
      const existing = state.cart.find(item => item.productId === action.id);
      return { ...state, cart: existing
        ? state.cart.map(item => item.productId === action.id ? { ...item, quantity: item.quantity + 1 } : item)
        : [...state.cart, { productId: action.id, quantity: 1 }] };
    }
    case 'cart/quantity':
      return { ...state, cart: state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.max(1, action.quantity) } : item) };
    case 'cart/remove': return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
    case 'product/add': return { ...state, products: [...state.products, action.product] };
    case 'product/update': return { ...state, products: state.products.map(item => item.id === action.product.id ? action.product : item) };
    case 'product/delete': return { ...state, products: state.products.filter(item => item.id !== action.id) };
    case 'product/status': return { ...state, products: state.products.map(item => item.id === action.id ? { ...item, status: action.status } : item) };
    default: return state;
  }
}

