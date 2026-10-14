import { Link, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { LoginPage, RegisterPage, RoleSelectionPage } from './pages/LoginPages';
import { BuyerDashboard, CartPage, ProductDetailsPage } from './pages/BuyerPages';
import { ProductFormPage, SellerDashboard, SellerProfilePage } from './pages/SellerPages';
import { AdminDashboard } from './pages/AdminDashboard';
import { AddressPage } from './pages/AddressPage';
import { BuyerProfilePage, OrderDetailsPage, OrderHistoryPage } from './pages/OrderPages';
import { WhatsAppButton } from './components/Shared';
import { Loading } from './components/ApiStates';
import { AuthProvider, roleHome, useAuth } from './state/AuthContext';
import { DemoProvider } from './state/DemoContext';
import type { Role } from './api/types';
function RequireRole({role}:{role:Role}){const auth=useAuth();if(auth.loading)return <Loading/>;if(!auth.user)return <Navigate to={`/login/${role.toLowerCase()}`} replace/>;if(auth.user.role!==role)return <div className="permission-page"><h1>This page is not available for your account.</h1><Link className="btn btn-primary" to={roleHome(auth.user.role)}>Open your workspace</Link></div>;return <Outlet/>;}
function Application(){const {user}=useAuth();return <DemoProvider key={user?`${user.id}:${user.role}`:"anonymous"}><Routes>
  <Route path="/" element={<LandingPage/>}/><Route path="/login" element={<RoleSelectionPage/>}/><Route path="/login/:role" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer" element={<BuyerDashboard/>}/><Route path="/buyer/profile" element={<BuyerProfilePage/>}/><Route path="/buyer/products/:id" element={<ProductDetailsPage/>}/><Route path="/buyer/cart" element={<CartPage/>}/><Route path="/buyer/addresses" element={<AddressPage/>}/><Route path="/buyer/orders" element={<OrderHistoryPage/>}/><Route path="/buyer/orders/:id" element={<OrderDetailsPage/>}/></Route>
  <Route element={<RequireRole role="SELLER"/>}><Route path="/seller" element={<SellerDashboard/>}/><Route path="/seller/profile" element={<SellerProfilePage/>}/><Route path="/seller/products/new" element={<ProductFormPage/>}/><Route path="/seller/products/:id/edit" element={<ProductFormPage/>}/><Route path="/seller/addresses" element={<AddressPage/>}/><Route path="/seller/orders" element={<OrderHistoryPage/>}/><Route path="/seller/orders/:id" element={<OrderDetailsPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin" element={<AdminDashboard/>}/><Route path="/admin/addresses" element={<AddressPage/>}/></Route>
  <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes><WhatsAppButton/></DemoProvider>;}
export default function App(){return <AuthProvider><Application/></AuthProvider>;}
