import type { Category } from '../types';

export interface ProductInput { name: string; description: string; category: Category; price: number | string; stock: number | string; seller: string; radius: 1 | 2 | 3 }
export function validateProduct(value: ProductInput) {
  const errors: Record<string, string> = {};
  if (!value.name.trim()) errors.name = 'Required';
  if (!value.description.trim()) errors.description = 'Required';
  if (!value.seller.trim()) errors.seller = 'Required';
  if (!['Handmade','Home Decor','Gifts','Fashion','Jewellery','Crafts'].includes(value.category)) errors.category = 'Choose a valid category';
  if (![1,2,3].includes(value.radius)) errors.radius = 'Choose a 1, 2 or 3 km delivery radius';
  const price = Number(value.price), stock = Number(value.stock);
  if (value.price === '' || !Number.isFinite(price) || price <= 0) errors.price = 'Enter a positive price';
  if (value.stock === '' || !Number.isInteger(stock) || stock < 0) errors.stock = 'Enter a valid quantity';
  return errors;
}
