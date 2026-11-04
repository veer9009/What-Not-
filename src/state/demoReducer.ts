import type { DemoAction, DemoState } from '../types';
import { isBuyerEligible } from '../utils/products';
import { createSellerOrders } from '../utils/orders';
import { validateProduct } from '../utils/validation';
import { identifier } from '../api/client';

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case 'cart/add-discovered': {
      const p = action.product;
      try { identifier(p.id); identifier(p.seller_id); } catch { return state; }
      const product = { id: `backend:${p.id}`, name: p.name, seller: p.shop_name, price: Number(p.price),
        distance: 0, radius: p.delivery_radius_km, stock: p.stock_quantity, category: p.category,
        description: p.description, image: p.image_url ?? '', verified: p.is_verified, rating: 0,
        status: 'APPROVED' as const, isActive: true, backend: { productId: p.id, sellerId: p.seller_id, unitPrice:p.price } };
      if (!isBuyerEligible(product) || !Number.isFinite(product.price) || product.price <= 0) return state;
      const products = [...state.products.filter(item => item.id !== product.id), product];
      return demoReducer({ ...state, products }, { type: 'cart/add', id: product.id });
    }
    case 'cart/placement': {
      let placements = state.placements ?? [];
      if (action.attempt) placements = [...placements.filter(item => item.key !== action.attempt!.key), action.attempt];
      placements = placements.flatMap(attempt => attempt.cartIds.some(id=>action.ids.includes(id))
        ? action.uncertain ? [{ ...attempt, pending: action.pending ?? false }] : [] : [attempt]);
      return { ...state, placements, cart: state.cart.map(item => action.ids.includes(item.productId)
        ? { ...item, placementUncertain: action.uncertain, placementPending: action.pending ?? false } : item) };
    }
    case 'cart/ordered': return { ...state, cart: state.cart.filter(item => !action.ids.includes(item.productId)),
      placements: (state.placements ?? []).filter(attempt=>!attempt.cartIds.some(id=>action.ids.includes(id))) };
    case 'cart/add': {
      const product = state.products.find(item => item.id === action.id);
      if (!product || !isBuyerEligible(product)) return state;
      const existing = state.cart.find(item => item.productId === action.id);
      if (existing?.placementUncertain || state.placements?.some(attempt=>attempt.cartIds.includes(action.id))) return state;
      return { ...state, cart: existing
        ? state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, item.quantity + 1) } : item)
        : [...state.cart, { productId: action.id, quantity: 1 }] };
    }
    case 'cart/quantity': {
      if (state.cart.find(item => item.productId === action.id)?.placementUncertain) return state;
      const product = state.products.find(item => item.id === action.id);
      if (!product || !isBuyerEligible(product)) return { ...state, cart: state.cart.filter(item => item.productId !== action.id) };
      if (!Number.isInteger(action.quantity)) return state;
      return { ...state, cart: state.cart.map(item => item.productId === action.id ? { ...item, quantity: Math.min(product.stock, Math.max(1, action.quantity)) } : item) };
    }
    case 'cart/remove': return { ...state, cart: state.cart.filter(item => item.productId !== action.id || item.placementUncertain) };
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
      if (state.cart.some(item => state.products.find(product => product.id === item.productId)?.backend)) return state;
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
