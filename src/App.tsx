import { Navigate, Route, Routes } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { LoginPage, RoleSelectionPage } from './pages/LoginPages';
import { BuyerDashboard, CartPage, ProductDetailsPage } from './pages/BuyerPages';
import { ProductFormPage, SellerDashboard } from './pages/SellerPages';
import { AdminDashboard } from './pages/AdminDashboard';
import { WhatsAppButton } from './components/Shared';

export default function App() {
  return <><Routes>
    <Route path="/" element={<LandingPage />} />
    <Route path="/login" element={<RoleSelectionPage />} />
    <Route path="/login/:role" element={<LoginPage />} />
    <Route path="/buyer" element={<BuyerDashboard />} />
    <Route path="/buyer/products/:id" element={<ProductDetailsPage />} />
    <Route path="/buyer/cart" element={<CartPage />} />
    <Route path="/seller" element={<SellerDashboard />} />
    <Route path="/seller/products/new" element={<ProductFormPage />} />
    <Route path="/seller/products/:id/edit" element={<ProductFormPage />} />
    <Route path="/admin" element={<AdminDashboard />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes><WhatsAppButton /></>;
}

