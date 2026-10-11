import type { DemoAction, DemoState } from '../types';
import { isBuyerEligible } from '../utils/products';
import { createSellerOrders } from '../utils/orders';
import { validateProduct } from '../utils/validation';

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case 'cart/add': {
      const product = state.products.find(item => item.id === action.id);
      if (!product || !isBuyerEligible(product)) return state;
      const existing = state.cart.find(item => item.productId === action.id);
      return { ...state, cart: existing
        ? state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, item.quantity + 1) } : item)
        : [...state.cart, { productId: action.id, quantity: 1 }] };
    }
    case 'cart/quantity': {
      const product = state.products.find(item => item.id === action.id);
      if (!product || !isBuyerEligible(product)) return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
      if (!Number.isInteger(action.quantity)) return state;
      return { ...state, cart: state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, Math.max(1, action.quantity)) } : item) };
    }
    case 'cart/remove': return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
    case 'product/add': {
      if (action.product.seller !== action.seller || state.products.some(p => p.id === action.product.id) || Object.keys(validateProduct(action.product)).length) return state;
      return { ...state, products: [...state.products, { ...action.product, status: 'PENDING', isActive: true, rejectionReason: undefined }] };
    }
    case 'product/update': {
      const previous = state.products.find(p => p.id === action.product.id);
      if (!previous || previous.seller !== action.seller || action.product.seller !== action.seller || Object.keys(validateProduct(action.product)).length) return state;
      const product = { ...action.product, seller: previous.seller, distance: previous.distance, rating: previous.rating, verified: previous.verified,
        isActive: previous.isActive, status: previous.status === 'REJECTED' ? 'REJECTED' as const : 'PENDING' as const,
        rejectionReason: previous.status === 'REJECTED' ? previous.rejectionReason : undefined };
      return { ...state, products: state.products.map(p => p.id === product.id ? product : p), cart: state.cart.filter(item => item.productId !== product.id) };
    }
    case 'product/delete':
    case 'product/active':
    case 'product/resubmit': {
      const product = state.products.find(p => p.id === action.id);
      if (!product || product.seller !== action.seller) return state;
      if (action.type === 'product/delete') return { ...state, products: state.products.filter(p => p.id !== action.id), cart: state.cart.filter(item => item.productId !== action.id) };
      if (action.type === 'product/resubmit' && (product.status !== 'REJECTED' || Object.keys(validateProduct(product)).length)) return state;
      return { ...state, products: state.products.map(p => p.id === action.id ? action.type === 'product/active'
        ? { ...p, isActive: action.isActive } : { ...p, status: 'PENDING', rejectionReason: undefined } : p),
        cart: state.cart.filter(item => item.productId !== action.id) };
    }
    case 'product/status': {
      const product = state.products.find(p => p.id === action.id);
      if (action.role !== 'admin' || !product || product.status !== 'PENDING' || !['APPROVED', 'REJECTED'].includes(action.status)) return state;
      const reason = action.rejectionReason?.trim();
      if (action.status === 'REJECTED' && !reason) return state;
      return { ...state, products: state.products.map(p => p.id === action.id ? { ...p, status: action.status, rejectionReason: action.status === 'REJECTED' ? reason : undefined } : p),
        cart: state.cart.filter(item => item.productId !== action.id) };
    }
    case 'checkout': {
      const orders = createSellerOrders(state.products, state.cart, action.id);
      if (!orders.length || orders.some(order => state.orders.some(existing => existing.id === order.id))) return state;
      return { ...state, orders: [...state.orders, ...orders], cart: [], products: state.products.map(p => {
        const item = state.cart.find(item => item.productId === p.id);
        return item ? { ...p, stock: p.stock - item.quantity } : p;
      }) };
    }
    default: return state;
  }
}
