// ==============================================================================
// CU20 - GENERAR REPORTES Y DASHBOARDS -> VISTA EJECUTIVA (ANGULAR 18)
// Ubicación: frontend-web/src/app/views/dashboard/dashboard.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  ReporteService,
  DashboardKPIs,
  VentasPorSucursal,
  VentasPorCanal,
  VentasPorMetodoPago,
  TopPrenda
} from '../../services/cu20_generar_reportes_dashboards/reporte.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatDividerModule,
    MatTooltipModule
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  nombreUsuario = '';
  rolUsuario = '';
  tenantNombre = 'Shopyn Golden Store';
  planNombre = 'Profesional';
  loading = true;
  filtroDias: number | undefined = undefined;

  kpis: DashboardKPIs | null = null;
  ventasSucursal: VentasPorSucursal[] = [];
  ventasCanal: VentasPorCanal[] = [];
  ventasMetodo: VentasPorMetodoPago[] = [];
  topPrendas: TopPrenda[] = [];

  constructor(
    private reporteService: ReporteService,
    private router: Router
  ) {}

  ngOnInit(): void {
    const userStr = localStorage.getItem('usuario');
    const rolStr = localStorage.getItem('rol');
    this.tenantNombre = localStorage.getItem('tenant_nombre') || 'Shopyn Golden Store';
    const planStr = localStorage.getItem('tenant_plan');
    if (planStr) {
      try {
        this.planNombre = JSON.parse(planStr).nombre || 'Profesional';
      } catch {}
    }
    if (userStr) {
      try {
        const u = JSON.parse(userStr);
        this.nombreUsuario = u.nombre || 'Administrador';
      } catch (e) {
        this.nombreUsuario = 'Administrador';
      }
    }
    this.rolUsuario = rolStr || 'ADMIN';
    this.cargarReportes();
  }

  cargarReportes(): void {
    this.loading = true;

    this.reporteService.getKPIs(this.filtroDias).subscribe({
      next: (k) => this.kpis = k,
      error: (err) => console.error('Error KPIs:', err)
    });

    this.reporteService.getVentasPorSucursal().subscribe({
      next: (s) => this.ventasSucursal = s,
      error: (err) => console.error('Error Sucursales:', err)
    });

    this.reporteService.getVentasPorCanal().subscribe({
      next: (c) => this.ventasCanal = c,
      error: (err) => console.error('Error Canales:', err)
    });

    this.reporteService.getVentasPorMetodoPago().subscribe({
      next: (m) => this.ventasMetodo = m,
      error: (err) => console.error('Error Metodos:', err)
    });

    this.reporteService.getTopPrendas(5).subscribe({
      next: (p) => {
        this.topPrendas = p;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error Top Prendas:', err);
        this.loading = false;
      }
    });
  }

  cambiarFiltro(dias?: number): void {
    this.filtroDias = dias;
    this.cargarReportes();
  }

  exportarCSV(): void {
    this.reporteService.descargarCSV();
  }

  imprimirReporte(): void {
    window.print();
  }

  logout(): void {
    localStorage.clear();
    this.router.navigate(['/login']);
  }

  getPorcentajeSucursal(monto: number): number {
    if (!this.kpis || this.kpis.total_ingresos_bs <= 0) return 0;
    return Math.min(100, Math.round((monto / this.kpis.total_ingresos_bs) * 100));
  }

  getPorcentajeMetodo(monto: number): number {
    if (!this.kpis || this.kpis.total_ingresos_bs <= 0) return 0;
    return Math.min(100, Math.round((monto / this.kpis.total_ingresos_bs) * 100));
  }
}
