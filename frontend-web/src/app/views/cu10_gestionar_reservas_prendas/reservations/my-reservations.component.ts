// ==============================================================================
// CAPA VISTA / CONTROLADOR (MVC - VIEW & CONTROLLER EN FRONTEND ANGULAR)
// Módulo: CU10 - Gestionar Reservas de Prendas
// Ubicación: frontend-web/src/app/views/reservations/my-reservations.component.ts
// ==============================================================================

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ReservationService } from '../../../services/cu10_gestionar_reservas_prendas/reservation.service';
import { Reserva } from '../../../models/cu10_gestionar_reservas_prendas/reservation.model';

@Component({
  selector: 'app-my-reservations',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule
  ],
  templateUrl: './my-reservations.component.html',
  styleUrls: ['./my-reservations.component.css']
})
export class MyReservationsComponent implements OnInit {
  reservas: Reserva[] = [];
  reservasFiltradas: Reserva[] = [];
  filtroActual: 'TODAS' | 'PENDIENTE' | 'ENTREGADA' | 'CANCELADA' = 'TODAS';
  loading = true;
  cancelandoId: number | null = null;
  copiadoId: number | null = null;
  isAdminView = false;

  constructor(
    private reservationService: ReservationService,
    private router: Router
  ) {
    this.isAdminView = this.router.url.startsWith('/admin');
  }

  ngOnInit(): void {
    this.cargarReservas();
  }

  cargarReservas(): void {
    this.loading = true;
    const obs$ = this.isAdminView
      ? this.reservationService.getReservasAdmin()
      : this.reservationService.getMisReservas();

    obs$.subscribe({
      next: (res) => {
        this.reservas = res;
        this.aplicarFiltro(this.filtroActual);
        this.loading = false;
      },
      error: (err) => {
        console.error('Error al cargar reservas:', err);
        this.loading = false;
      }
    });
  }

  aplicarFiltro(filtro: 'TODAS' | 'PENDIENTE' | 'ENTREGADA' | 'CANCELADA'): void {
    this.filtroActual = filtro;
    if (filtro === 'TODAS') {
      this.reservasFiltradas = [...this.reservas];
    } else {
      this.reservasFiltradas = this.reservas.filter(r => r.estado === filtro);
    }
  }

  copiarCodigo(codigo: string, id: number): void {
    navigator.clipboard.writeText(codigo).then(() => {
      this.copiadoId = id;
      setTimeout(() => this.copiadoId = null, 2500);
    });
  }

  cancelar(reserva: Reserva): void {
    if (reserva.estado !== 'PENDIENTE') {
      alert('Solo se pueden cancelar reservas que se encuentren en estado PENDIENTE.');
      return;
    }

    const motivo = prompt('¿Por qué deseas cancelar esta reserva? (Opcional):', 'Cambio de planes');
    if (motivo === null) return; // Canceló el prompt

    this.cancelandoId = reserva.id;
    this.reservationService.cancelarReserva(reserva.id, motivo || 'Cancelada por cliente').subscribe({
      next: (actualizada) => {
        this.cancelandoId = null;
        alert(`La reserva ${actualizada.codigo_reserva} ha sido cancelada. El inventario ha sido liberado.`);
        this.cargarReservas();
      },
      error: (err) => {
        this.cancelandoId = null;
        alert(err.error?.detail || 'Error al cancelar la reserva');
      }
    });
  }

  get pendientesCount(): number {
    return this.reservas.filter(r => r.estado === 'PENDIENTE').length;
  }

  get entregadasCount(): number {
    return this.reservas.filter(r => r.estado === 'ENTREGADA').length;
  }

  get pendientesOfflineCount(): number {
    return this.reservationService.obtenerReservasOfflinePendientes().length;
  }

  sincronizarReservasOffline(): void {
    this.reservationService.sincronizarReservasOffline().subscribe({
      next: (creadas) => {
        if (creadas && creadas.length > 0) {
          alert(`✅ Se sincronizaron ${creadas.length} reserva(s) offline con el servidor central.`);
          this.cargarReservas();
        } else {
          alert('⚠️ Desactiva primero el Modo Sin Internet en el Catálogo para sincronizar con el servidor.');
        }
      }
    });
  }

  irAAtenderEnCaja(res: Reserva): void {
    this.router.navigate(['/admin/reservas'], { queryParams: { codigo: res.codigo_reserva } });
  }

  // --- Modal Ticket Digital de Reserva (CU10 Senior Feature) ---
  ticketReserva: Reserva | null = null;

  abrirTicket(r: Reserva): void {
    this.ticketReserva = r;
  }

  cerrarTicket(): void {
    this.ticketReserva = null;
  }

  imprimirTicket(): void {
    window.print();
  }
}
