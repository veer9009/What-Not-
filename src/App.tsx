import { Link, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { LoginPage, RegisterPage } from './pages/LoginPages';
import { PasswordRecoveryPage } from './pages/PasswordRecoveryPage';
import { BuyerDashboard, CartPage, ProductDetailsPage } from './pages/BuyerPages';
import { ProductFormPage, SellerDashboard, SellerProfilePage } from './pages/SellerPages';
import { AdminDashboard } from './pages/AdminDashboard';
import { AddressPage } from './pages/AddressPage';
import { HelpPage } from './pages/HelpPage';
import { BuyerProfilePage, OrderDetailsPage, OrderHistoryPage } from './pages/OrderPages';
import { PublicSidebar, WhatsAppButton } from './components/Shared';
import { Loading } from './components/ApiStates';
import { AuthProvider, roleHome, useAuth } from './state/AuthContext';
import { DemoProvider } from './state/DemoContext';
import { DiscoveryProvider } from './state/DiscoveryContext';
import { BuyerDiscoveryPage, DiscoveryDetailPage } from './pages/DiscoveryPages';
import { NotificationsPage } from './pages/NotificationsPage';
import { AdminOperationsPage, CreativeModerationPage } from './pages/AdminOperations';
import { BuyerCreativePage, SellerCreativePage } from './pages/CreativePages';
import { PublicServiceCatalog } from './pages/ServiceCatalog';
import { PropertyBrowsePage, PropertyDetailPage, PropertyManagePage, PropertyRequestsPage, PropertyModerationPage } from './pages/PropertyPages';
import type { Role } from './api/types';
import { LegalPage } from './pages/LegalPages';
import { LegalFooter } from './components/LegalNavigation';
import { PaymentsPage } from './pages/PaymentsPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { WishlistPage } from './pages/WishlistPage';
import { WishlistProvider } from './state/WishlistContext';
import { SellerPaymentSettingsPage, AdminPaymentSettingsPage } from './pages/PaymentSettingsPages';
function RequireRole({role}:{role:Role}){const auth=useAuth();if(auth.loading)return <Loading/>;if(!auth.user)return <Navigate to={role==='ADMIN'?'/admin/login':`/login/${role.toLowerCase()}`} replace/>;if(auth.user.role!==role)return <div className="permission-page"><h1>This page is not available for your account.</h1><Link className="btn btn-primary" to={roleHome(auth.user.role)}>Open your workspace</Link></div>;return <Outlet/>;}
function Application(){const {user}=useAuth();const {pathname}=useLocation();const authenticationPage=/^\/(login(?:\/|$)|register$|forgot-password$|admin\/login$)/.test(pathname);return <DiscoveryProvider key={user?`${user.id}:${user.role}`:'anonymous'}><WishlistProvider><DemoProvider ownerId={user?.role==='BUYER'?user.id:undefined} key={user?`${user.id}:${user.role}`:"anonymous"}>{authenticationPage&&<PublicSidebar/>}<Routes>
  <Route path="/privacy" element={<LegalPage kind="privacy"/>}/><Route path="/terms" element={<LegalPage kind="terms"/>}/><Route path="/cookies" element={<LegalPage kind="cookies"/>}/><Route path="/refunds" element={<LegalPage kind="refunds"/>}/><Route path="/contact" element={<LegalPage kind="contact"/>}/><Route path="/support" element={<LegalPage kind="contact"/>}/>
  <Route path="/" element={<LandingPage/>}/><Route path="/creative-services" element={<PublicServiceCatalog domain="CREATIVE"/>}/><Route path="/professional-services" element={<PublicServiceCatalog domain="PROFESSIONAL"/>}/><Route path="/login" element={<LoginPage/>}/><Route path="/login/:role" element={<LoginPage/>}/><Route path="/forgot-password" element={<PasswordRecoveryPage/>}/><Route path="/register" element={<RegisterPage/>}/>
  <Route path="/admin/login" element={<LoginPage administration/>}/><Route path="/login/admin" element={<Navigate to="/admin/login" replace/>}/>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer/payments" element={<PaymentsPage/>}/></Route>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer/checkout" element={<CheckoutPage/>}/><Route path="/buyer/wishlist" element={<WishlistPage/>}/></Route>
  <Route element={<RequireRole role="SELLER"/>}><Route path="/seller/payment-settings" element={<SellerPaymentSettingsPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin/payment-settings" element={<AdminPaymentSettingsPage/>}/></Route>
  <Route element={<RequireRole role="SELLER"/>}><Route path="/seller/payments" element={<PaymentsPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin/payments" element={<PaymentsPage/>}/></Route>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer" element={<BuyerDiscoveryPage/>}/><Route path="/buyer/samples" element={<BuyerDashboard/>}/><Route path="/buyer/samples/products/:id" element={<ProductDetailsPage/>}/><Route path="/buyer/profile" element={<BuyerProfilePage/>}/><Route path="/buyer/products/:id" element={<DiscoveryDetailPage/>}/><Route path="/buyer/cart" element={<CartPage/>}/><Route path="/buyer/addresses" element={<AddressPage/>}/><Route path="/buyer/orders" element={<OrderHistoryPage/>}/><Route path="/buyer/orders/:id" element={<OrderDetailsPage/>}/></Route>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer/help" element={<HelpPage/>}/></Route>
  <Route element={<RequireRole role="BUYER"/>}><Route path="/buyer/notifications" element={<NotificationsPage/>}/><Route path="/buyer/creative" element={<BuyerCreativePage/>}/><Route path="/buyer/professional" element={<BuyerCreativePage domain="PROFESSIONAL"/>}/><Route path="/buyer/properties" element={<PropertyBrowsePage/>}/><Route path="/buyer/properties/saved" element={<PropertyBrowsePage saved/>}/><Route path="/buyer/properties/requests" element={<PropertyRequestsPage/>}/><Route path="/buyer/properties/:id" element={<PropertyDetailPage/>}/></Route>
  <Route element={<RequireRole role="SELLER"/>}><Route path="/seller/notifications" element={<NotificationsPage/>}/><Route path="/seller/creative" element={<SellerCreativePage/>}/><Route path="/seller/professional" element={<SellerCreativePage domain="PROFESSIONAL"/>}/><Route path="/seller/properties" element={<PropertyManagePage/>}/><Route path="/seller/properties/requests" element={<PropertyRequestsPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin/notifications" element={<NotificationsPage/>}/><Route path="/admin/properties" element={<PropertyModerationPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin/operations" element={<AdminOperationsPage/>}/><Route path="/admin/creative" element={<CreativeModerationPage/>}/></Route>
  <Route element={<RequireRole role="SELLER"/>}><Route path="/seller" element={<SellerDashboard/>}/><Route path="/seller/profile" element={<SellerProfilePage/>}/><Route path="/seller/products/new" element={<ProductFormPage/>}/><Route path="/seller/products/:id/edit" element={<ProductFormPage/>}/><Route path="/seller/addresses" element={<AddressPage/>}/><Route path="/seller/orders" element={<OrderHistoryPage/>}/><Route path="/seller/orders/:id" element={<OrderDetailsPage/>}/></Route>
  <Route element={<RequireRole role="ADMIN"/>}><Route path="/admin" element={<AdminDashboard/>}/><Route path="/admin/addresses" element={<AddressPage/>}/></Route>
  <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes><LegalFooter/><WhatsAppButton/></DemoProvider></WishlistProvider></DiscoveryProvider>;}
export default function App(){return <AuthProvider><a className="skip-link" href="#main-content" onClick={()=>document.getElementById('main-content')?.focus()}>Skip to main content</a><Application/></AuthProvider>;}
