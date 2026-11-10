import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatBadgeModule } from '@angular/material/badge';

import { NotificacionService, NotificacionDTO } from '../../../services/cu19_gestionar_notificaciones/notificacion.service';
import { AuthService } from '../../../core/services/auth.service';
import { SuscripcionTenantService } from '../../../services/cu21_administrar_planes_suscripcion_tenants/suscripcion-tenant.service';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatSidenavModule,
    MatToolbarModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    MatBadgeModule
  ],
  templateUrl: './admin-layout.component.html',
  styleUrls: ['./admin-layout.component.css']
})
export class AdminLayoutComponent implements OnInit {
  userEmail: string = 'admin@tienda.com';
  userName: string = 'Administrador';
  isSuperAdmin: boolean = false;
  tenantNombre: string = 'Shopyn Golden Store';
  tenantSlug: string = 'goldenstore';
  planNombre: string = 'Profesional';
  limiteSucursales: number = 10;
  tieneReportesIA: boolean = true;

  constructor(
    public notifService: NotificacionService,
    private router: Router,
    private authService: AuthService,
    private tenantService: SuscripcionTenantService
  ) {}

  ngOnInit(): void {
    this.isSuperAdmin = this.authService.esSuperAdmin();
    this.tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';
    this.tenantSlug = localStorage.getItem('tenant_slug') || 'goldenstore';

    const planStr = localStorage.getItem('tenant_plan');
    if (planStr) {
      try {
        const p = JSON.parse(planStr);
        this.planNombre = p.nombre || 'Profesional';
        this.limiteSucursales = p.limite_sucursales || 2;
        this.tieneReportesIA = !!(p.habilitar_reportes_ia ?? p.habilitar_vestidor_ia);
      } catch {}
    }

    // Sincronizar en tiempo real el Plan actual que el Administrador General le dio a este Tenant
    if (!this.isSuperAdmin) {
      this.tenantService.obtenerMiPlan().subscribe({
        next: (res) => {
          if (res.exito && res.tenant) {
            this.tenantNombre = res.tenant.nombre || this.tenantNombre;
            this.tenantSlug = res.tenant.slug || this.tenantSlug;
            localStorage.setItem('tenant_nombre', this.tenantNombre);
            localStorage.setItem('tenant_slug', this.tenantSlug);
            if (res.tenant.plan) {
              const p = res.tenant.plan;
              this.planNombre = p.nombre;
              this.limiteSucursales = p.limite_sucursales;
              this.tieneReportesIA = !!(p.habilitar_reportes_ia ?? p.habilitar_vestidor_ia);
              localStorage.setItem('tenant_plan', JSON.stringify(p));
            }
          }
        },
        error: () => {}
      });
    }

    this.notifService.cargarNotificaciones();
    const userStr = localStorage.getItem('user') || localStorage.getItem('usuario');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.userName = user.nombre || 'Administrador';
        this.userEmail = user.email || 'admin@tienda.com';
      } catch (e) {
        console.error('Error al cargar datos del usuario', e);
      }
    }
  }

  abrirReportesIA(): void {
    if (!this.tieneReportesIA) {
      alert(
        `🔒 Función Restringida por Plan:\n\nSu negocio "${this.tenantNombre}" cuenta actualmente con el Plan ${this.planNombre} (Hasta ${this.limiteSucursales} sucursales, sin Reportes Generativos con IA).\n\nSolicite al Administrador General del Sistema el upgrade al Plan Profesional para habilitar los Reportes Generativos con IA.`
      );
      return;
    }
    this.router.navigate(['/admin/reportes-ia']);
  }

  navegarNotificacion(notif: NotificacionDTO): void {
    this.notifService.marcarLeida(notif.id).subscribe();
    if (notif.enlace) {
      this.router.navigate([notif.enlace]);
    }
  }

  marcarTodasLeidas(): void {
    this.notifService.marcarTodasLeidas().subscribe();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}

