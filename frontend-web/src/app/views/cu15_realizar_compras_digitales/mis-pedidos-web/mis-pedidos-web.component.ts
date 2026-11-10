import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';

import { HistorialService, CompraHistorialDTO, ResumenClienteDTO } from '../../../services/cu17_consultar_historial_compras_reservas/historial.service';

@Component({
  selector: 'app-mis-pedidos-web',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatDividerModule,
    MatChipsModule
  ],
  templateUrl: './mis-pedidos-web.component.html',
  styleUrls: ['./mis-pedidos-web.component.css']
})
export class MisPedidosWebComponent implements OnInit {
  compras: CompraHistorialDTO[] = [];
  resumen: ResumenClienteDTO | null = null;
  loading = true;
  isAdminView = false;

  constructor(
    private historialService: HistorialService,
    private router: Router
  ) {
    this.isAdminView = this.router.url.startsWith('/admin');
  }

  ngOnInit(): void {
    this.cargarDatos();
  }

  cargarDatos(): void {
    this.loading = true;
    this.historialService.obtenerResumen().subscribe({
      next: (res) => this.resumen = res,
      error: (e) => console.warn('No se pudo cargar resumen:', e)
    });

    this.historialService.obtenerCompras().subscribe({
      next: (data) => {
        this.compras = data;
        this.loading = false;
      },
      error: (e) => {
        console.error('Error al cargar historial de compras:', e);
        this.loading = false;
      }
    });
  }

  volverATienda(): void {
    this.router.navigate([this.isAdminView ? '/admin/catalogo' : '/catalogo']);
  }

  verComprobante(ventaId: number): void {
    const host = typeof window !== 'undefined' && window.location ? window.location.hostname : 'localhost';
    const url = `http://${host}:8000/api/v1/pagos/${ventaId}/comprobante-html`;
    window.open(url, '_blank');
  }

  getOrderStep(estado: string): number {
    const s = (estado || '').toUpperCase();
    if (s.includes('PREPAR') || s.includes('CONFIRMAD')) return 1;
    if (s.includes('CAMINO') || s.includes('ENVIAD') || s.includes('TRANSITO')) return 2;
    if (s.includes('ENTREGAD') || s.includes('COMPLETAD') || s.includes('FINALIZAD')) return 3;
    return 0; // REGISTRADO
  }
}
