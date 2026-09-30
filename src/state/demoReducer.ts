import type { DemoAction, DemoState } from '../types';

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case 'cart/add': {
      const product = state.products.find(item => item.id === action.id);
      if (!product || product.status !== 'approved' || product.distance > product.radius || product.stock < 1) return state;
      const existing = state.cart.find(item => item.productId === action.id);
      return { ...state, cart: existing
        ? state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, item.quantity + 1) } : item)
        : [...state.cart, { productId: action.id, quantity: 1 }] };
    }
    case 'cart/quantity': {
      const product = state.products.find(item => item.id === action.id);
      if (!product) return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
      return { ...state, cart: state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, Math.max(1, action.quantity)) } : item) };
    }
    case 'cart/remove': return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
    case 'product/add': return { ...state, products: [...state.products, action.product] };
    case 'product/update': return { ...state, products: state.products.map(item => item.id === action.product.id ? action.product : item), cart: state.cart.filter(item => item.productId !== action.product.id) };
    case 'product/delete': return { ...state, products: state.products.filter(item => item.id !== action.id), cart: state.cart.filter(item => item.productId !== action.id) };
    case 'product/status': return { ...state, products: state.products.map(item => item.id === action.id ? { ...item, status: action.status } : item), cart: action.status === 'approved' ? state.cart : state.cart.filter(item => item.productId !== action.id) };
    default: return state;
  }
}
