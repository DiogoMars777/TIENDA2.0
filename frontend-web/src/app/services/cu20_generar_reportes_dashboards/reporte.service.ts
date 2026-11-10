import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { DashboardService } from '../cu27_dashboard_ejecutivo/dashboard.service';
import {
  DashboardKPIs,
  VentaPorSucursal,
  VentaPorCanal,
  VentaPorMetodoPago,
  TopPrenda
} from '../../models/cu27_dashboard_ejecutivo/dashboard.model';

export type { DashboardKPIs, TopPrenda };
export type VentasPorSucursal = VentaPorSucursal;
export type VentasPorCanal = VentaPorCanal;
export type VentasPorMetodoPago = VentaPorMetodoPago;

@Injectable({
  providedIn: 'root'
})
export class ReporteService {
  constructor(private dashboardService: DashboardService) {}

  getKPIs(dias?: number): Observable<DashboardKPIs> {
    return this.dashboardService.obtenerKPIs(dias);
  }

  getVentasPorSucursal(dias?: number): Observable<VentasPorSucursal[]> {
    return this.dashboardService.obtenerVentasSucursal(dias);
  }

  getVentasPorCanal(dias?: number): Observable<VentasPorCanal[]> {
    return this.dashboardService.obtenerVentasCanal(dias);
  }

  getVentasPorMetodoPago(dias?: number): Observable<VentasPorMetodoPago[]> {
    return this.dashboardService.obtenerVentasMetodo(dias);
  }

  getTopPrendas(limite: number = 5, dias?: number): Observable<TopPrenda[]> {
    return this.dashboardService.obtenerTopPrendas(limite, dias);
  }

  descargarCSV(dias?: number): void {
    this.dashboardService.descargarCSV(dias);
  }
}
