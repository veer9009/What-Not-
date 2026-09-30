import type { Category } from '../types';

export interface ProductInput { name: string; description: string; category: Category; price: number; stock: number; seller: string; radius: 1 | 2 | 3 }
export function validateProduct(value: ProductInput) {
  const errors: Record<string, string> = {};
  if (!value.name.trim()) errors.name = 'Required';
  if (!value.description.trim()) errors.description = 'Required';
  if (!value.seller.trim()) errors.seller = 'Required';
  if (value.price <= 0) errors.price = 'Enter a positive price';
  if (!Number.isInteger(value.stock) || value.stock < 0) errors.stock = 'Enter a valid quantity';
  return errors;
}
