import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ListingImage } from './ListingImage';

it('preserves the supplied listing image and its accessible description', () => {
  render(<ListingImage src="https://example.test/vase.webp" alt="Handmade vase"/>);
  expect(screen.getByRole('img', { name: 'Handmade vase' })).toHaveAttribute('src', 'https://example.test/vase.webp');
  expect(screen.getByRole('img')).toHaveAttribute('referrerpolicy', 'no-referrer');
});

it('uses an accessible placeholder when a listing has no image', () => {
  render(<ListingImage src={null} alt="Handmade vase"/>);
  expect(screen.getByRole('img', { name: 'Handmade vase: image unavailable' })).toHaveTextContent('No photo yet');
});

it('handles a failed image and recovers when the listing URL changes', () => {
  const { rerender } = render(<ListingImage src="https://example.test/old.webp" alt="Handmade vase"/>);
  fireEvent.error(screen.getByRole('img'));
  expect(screen.getByRole('img', { name: 'Handmade vase: image unavailable' })).toBeInTheDocument();
  rerender(<ListingImage src="https://example.test/new.webp" alt="Handmade vase"/>);
  expect(screen.getByRole('img', { name: 'Handmade vase' })).toHaveAttribute('src', 'https://example.test/new.webp');
});
