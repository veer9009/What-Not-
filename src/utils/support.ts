import { identifier } from '../api/client';
import type { Id } from '../api/types';
import { business } from '../config/business';

export const SUPPORT_PHONE = business.supportPhone;

// Only the same public order reference shown in order history belongs in this URL.
export function supportUrl(orderId?: Id): string {
  const message = orderId === undefined
    ? 'Hi What Not Support, I need help with my marketplace account/order.'
    : `Hi What Not Support, I need help with Order #${identifier(orderId)}.`;
  return `https://wa.me/${business.supportWhatsApp}?text=${encodeURIComponent(message)}`;
}
