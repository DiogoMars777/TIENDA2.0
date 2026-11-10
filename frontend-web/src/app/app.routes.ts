import { Routes } from '@angular/router';

// CU1: Autenticación
import { LoginComponent } from './views/cu1_gestionar_autenticacion/login/login.component';
import { RegisterComponent } from './views/cu1_gestionar_autenticacion/register/register.component';
import { RecoverPasswordComponent } from './views/cu1_gestionar_autenticacion/recover-password.component';
import { ResetPasswordComponent } from './views/cu1_gestionar_autenticacion/reset-password.component';

// Dashboard & Layout
import { DashboardComponent } from './views/dashboard/dashboard.component';
import { AdminLayoutComponent } from './views/layout/admin-layout/admin-layout.component';
import { ClientLayoutComponent } from './views/layout/client-layout/client-layout.component';

// CU2: Usuarios y Roles
import { UserListComponent } from './views/cu2_gestionar_usuarios_roles/users/user-list/user-list.component';
import { RoleListComponent } from './views/cu2_gestionar_usuarios_roles/roles/role-list/role-list.component';

// CU3: Clientes
import { CustomerListComponent } from './views/cu3_gestionar_clientes/customers/customer-list/customer-list.component';

// CU4: Sucursales
import { SucursalListComponent } from './views/cu4_gestionar_sucursales/sucursales/sucursal-list/sucursal-list.component';

// CU5: Productos (Poleras)
import { ProductListComponent } from './views/cu5_gestionar_productos/products/product-list/product-list.component';

// CU6: Clasificación de Prendas (Categorías)
import { ClasificacionListComponent } from './views/cu6_gestionar_clasificacion_prendas/categorias/clasificacion-list/clasificacion-list.component';

// CU7: Proveedores y Suministros
import { ProveedorListComponent } from './views/cu7_gestionar_proveedores_productos_suministrados/suppliers/proveedor-list/proveedor-list.component';

// CU08: Catálogo y Disponibilidad Multitienda
import { ProductCatalogComponent } from './views/cu8_consultar_catalogo_disponibilidad/product-catalog/product-catalog.component';

// CU09: Carrito de Compras
import { CartViewComponent } from './views/cu9_gestionar_carrito_compras/cart/cart-view.component';

// CU10: Gestión de Reservas de Prendas
import { MyReservationsComponent } from './views/cu10_gestionar_reservas_prendas/reservations/my-reservations.component';

// CU11: Atender Reservas en Sucursal
import { AdminReservasComponent } from './views/cu11_atender_reservas_sucursal/admin-reservas/admin-reservas.component';

// CU13: Inventario y Movimientos de Poleras
import { InventarioListComponent } from './views/cu13_gestionar_inventario_movimientos/inventario/inventario-list/inventario-list.component';

// CU14: Registrar Ventas Presenciales (POS & Historial)
import { PosVentaComponent } from './views/cu14_registrar_ventas_presenciales/pos/pos-venta/pos-venta.component';
import { VentasListComponent } from './views/cu14_registrar_ventas_presenciales/ventas/ventas-list/ventas-list.component';

// CU15: Realizar Compras Digitales (Tienda Online & Mis Pedidos)
import { TiendaOnlineComponent } from './views/cu15_realizar_compras_digitales/tienda-online/tienda-online.component';
import { MisPedidosWebComponent } from './views/cu15_realizar_compras_digitales/mis-pedidos-web/mis-pedidos-web.component';

// CU16: Gestionar Pagos y Comprobantes
import { PagosListComponent } from './views/cu16_gestionar_pagos_comprobantes/pagos/pagos-list.component';

// CU17: Consultar Historial de Compras y Reservas
import { HistorialViewComponent } from './views/cu17_consultar_historial_compras_reservas/historial/historial-view.component';

// CU18: Gestionar Recomendaciones mediante IA
import { RecomendacionesViewComponent } from './views/cu18_gestionar_recomendaciones_ia/recomendaciones/recomendaciones-view.component';

// CU19: Gestionar Notificaciones
import { NotificacionesViewComponent } from './views/cu19_gestionar_notificaciones/notificaciones/notificaciones-view.component';

// CU20: Generar Reportes Generativos con IA
import { ReporteGenerativoComponent } from './views/cu20_generar_reportes_generativos_ia/reporte-generativo/reporte-generativo.component';

// CU21: Administrar Planes de Suscripción y Tenants
import { SuscripcionTenantListComponent } from './views/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant-list/suscripcion-tenant-list.component';

// CU22: Registrar Cobros de Contado Offline
import { CobroOfflineListComponent } from './views/cu22_registrar_cobros_contado_offline/cobro-offline-list/cobro-offline-list.component';

// CU23: Sincronizar Operaciones Offline y Resolver Conflictos
import { SincronizacionOfflineViewComponent } from './views/cu23_sincronizar_operaciones_offline/sincronizacion-offline-view/sincronizacion-offline-view.component';

// CU24: Gestionar Cancelación y Vencimiento de Reservas
import { VencimientoReservaViewComponent } from './views/cu24_gestionar_cancelacion_vencimiento_reservas/vencimiento-reserva-view/vencimiento-reserva-view.component';

// CU25: Gestionar Cambios y Devoluciones de Prendas
import { DevolucionListComponent } from './views/cu25_gestionar_cambios_devoluciones/devolucion-list/devolucion-list.component';

// CU26: Bitácora y Auditoría del Sistema
import { BitacoraListComponent } from './views/cu26_gestionar_bitacora/bitacora-list/bitacora-list.component';

// CU27: Dashboard Ejecutivo
import { DashboardEjecutivoComponent } from './views/cu27_dashboard_ejecutivo/dashboard-ejecutivo/dashboard-ejecutivo.component';

import { adminGuard, superAdminGuard } from './core/guards/admin.guard';
import { authGuard } from './core/guards/auth.guard';


export const routes: Routes = [
  // CU1: Autenticación
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'recover-password', component: RecoverPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },

  // Redirección para que el Dashboard siempre cargue dentro del layout con menú lateral
  { path: 'dashboard', redirectTo: 'admin/dashboard', pathMatch: 'full' },
  { path: 'reportes-ia', redirectTo: 'admin/reportes-ia', pathMatch: 'full' },
  { path: 'atencion-reservas', redirectTo: 'admin/reservas', pathMatch: 'full' },

  // Tienda y Portal del Cliente (Layout Omnicanal Boutique)
  {
    path: '',
    component: ClientLayoutComponent,
    children: [
      { path: 'catalogo', component: ProductCatalogComponent },
      { path: 'tienda', redirectTo: 'catalogo', pathMatch: 'full' },
      { path: 'carrito', component: CartViewComponent },
      { path: 'mis-reservas', component: MyReservationsComponent, canActivate: [authGuard] },
      { path: 'mis-pedidos', component: MisPedidosWebComponent, canActivate: [authGuard] },
      { path: 'historial', component: HistorialViewComponent, canActivate: [authGuard] },
      { path: 'recomendaciones', component: RecomendacionesViewComponent },
      { path: 'notificaciones', component: NotificacionesViewComponent, canActivate: [authGuard] },
      { path: 'tienda/mis-pedidos', redirectTo: 'mis-pedidos', pathMatch: 'full' },
      { path: '', redirectTo: 'catalogo', pathMatch: 'full' }
    ]
  },

  // Backoffice / Admin ERP (Protegido por adminGuard)
  {
    path: 'admin',
    component: AdminLayoutComponent,
    canActivate: [adminGuard],
    children: [
      // Dashboard dentro del layout con menú lateral fijo
      { path: 'dashboard', component: DashboardComponent },
      // CU2: Usuarios y Roles
      { path: 'users', component: UserListComponent },
      { path: 'roles', component: RoleListComponent },
      // CU26: Bitácora y Auditoría (Exclusivo SUPERADMIN)
      { path: 'bitacora', component: BitacoraListComponent, canActivate: [superAdminGuard] },
      // CU3: Clientes
      { path: 'customers', component: CustomerListComponent },
      // CU4: Sucursales
      { path: 'sucursales', component: SucursalListComponent },
      // CU6: Clasificación de Prendas
      { path: 'categorias', component: ClasificacionListComponent },
      // CU5: Poleras y Productos
      { path: 'products', component: ProductListComponent },
      // CU7: Proveedores
      { path: 'suppliers', component: ProveedorListComponent },
      // CU08: Catálogo
      { path: 'catalogo', component: ProductCatalogComponent },
      // CU09: Carrito
      { path: 'carrito', component: CartViewComponent },
      // CU10: Reservas
      { path: 'mis-reservas', component: MyReservationsComponent },
      // CU15: Mis Pedidos Online dentro de Admin
      { path: 'mis-pedidos', component: MisPedidosWebComponent },
      // CU11: Atender Reservas
      { path: 'reservas', component: AdminReservasComponent },
      // CU13: Inventario y Kardex
      { path: 'inventario', component: InventarioListComponent },
      // CU14: POS y Ventas
      { path: 'pos', component: PosVentaComponent },
      // CU15: Vitrina & Tienda Unificada
      { path: 'tienda-digital', redirectTo: '/catalogo', pathMatch: 'full' },
      { path: 'ventas', component: VentasListComponent },
      // CU16: Gestión de Pagos y Comprobantes
      { path: 'pagos', component: PagosListComponent },
      // CU17: Historial de Compras y Reservas
      { path: 'historial', component: HistorialViewComponent },
      // CU18: Recomendaciones mediante IA
      { path: 'recomendaciones', component: RecomendacionesViewComponent },
      // CU19: Gestión de Notificaciones
      { path: 'notificaciones', component: NotificacionesViewComponent },
      // CU20: Generar Reportes Generativos con IA
      { path: 'reportes-ia', component: ReporteGenerativoComponent },
      // CU21: Planes de Suscripción y Tenants (Exclusivo SUPERADMIN)
      { path: 'suscripciones-tenants', component: SuscripcionTenantListComponent, canActivate: [superAdminGuard] },
      // CU22: Cobros Contado Offline
      { path: 'cobros-offline', component: CobroOfflineListComponent },
      // CU23: Sincronización Offline
      { path: 'sincronizacion-offline', component: SincronizacionOfflineViewComponent },
      // CU24: Vencimiento de Reservas
      { path: 'vencimiento-reservas', component: VencimientoReservaViewComponent },
      // CU25: Cambios y Devoluciones
      { path: 'devoluciones', component: DevolucionListComponent },
      // CU27: Dashboard Ejecutivo
      { path: 'dashboard-ejecutivo', component: DashboardEjecutivoComponent },
      { path: '', redirectTo: 'users', pathMatch: 'full' }
    ]
  },

  { path: '**', redirectTo: 'catalogo' }
];
