import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

import { InventarioItem } from '../../../../models/cu13_gestionar_inventario_movimientos/inventario.model';
import { MetodoPago, VentaPresencialCreateDTO, VentaCompleta } from '../../../../models/cu14_registrar_ventas_presenciales/venta.model';
import { Sucursal } from '../../../../models/cu4_gestionar_sucursales/sucursal.model';
import { InventarioService } from '../../../../services/cu13_gestionar_inventario_movimientos/inventario.service';
import { VentaController } from '../../../../controllers/cu14_registrar_ventas_presenciales/venta.controller';
import { SucursalController } from '../../../../controllers/cu4_gestionar_sucursales/sucursal.controller';
import { ReceiptDialogComponent } from '../receipt-dialog/receipt-dialog.component';

// Servicios de Almacenamiento Offline en IndexedDB y Sincronización
import { PosIndexedDbService, VentaOfflineRecord } from '../../../../core/services/pos-indexed-db.service';
import { CobroOfflineService } from '../../../../services/cu22_registrar_cobros_contado_offline/cobro-offline.service';
import { RegistroCobroOfflineRequest } from '../../../../models/cu22_registrar_cobros_contado_offline/cobro-offline.model';

export interface PosCartItem {
  inventarioItem: InventarioItem;
  cantidad: number;
  precioUnitario: number;
  subtotal: number;
}

@Component({
  selector: 'app-pos-venta',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatDividerModule,
    MatSnackBarModule,
    MatProgressBarModule,
    MatDialogModule,
    MatTooltipModule,
    MatCheckboxModule
  ],
  templateUrl: './pos-venta.component.html',
  styleUrls: ['./pos-venta.component.css']
})
export class PosVentaComponent implements OnInit, OnDestroy {
  sucursales: Sucursal[] = [];
  metodosPago: MetodoPago[] = [];
  productosCatalogo: InventarioItem[] = [];
  productosFiltrados: InventarioItem[] = [];

  // Form Controls
  sucursalControl = new FormControl<number | null>(null, [Validators.required]);
  searchControl = new FormControl('');
  clienteNombreControl = new FormControl('Consumidor Final', [Validators.required]);
  clienteNitControl = new FormControl('0');
  metodoPagoControl = new FormControl<number | null>(null, [Validators.required]);
  montoRecibidoControl = new FormControl<number | null>(null);

  // Cart
  cart: PosCartItem[] = [];
  loading = false;
  procesandoVenta = false;
  private destroy$ = new Subject<void>();

  // Estado de Red & Modo Offline en IndexedDB
  isOnline: boolean = typeof navigator !== 'undefined' ? navigator.onLine : true;
  modoOfflineForzado: boolean = false;
  ventasPendientesSyncCount: number = 0;
  sincronizandoVentas: boolean = false;
  private autoSyncInterval: any = null;

  // QR Simulado
  qrConfirmadoManual = false;

  // Tarjeta Simulado
  tarjetaNumero = '4532 8920 1144 7820';
  tarjetaTitular = 'CONSUMIDOR FINAL';
  tarjetaVencimiento = '12/28';
  tarjetaCvv = '842';
  procesandoTarjeta = false;

  constructor(
    private inventarioService: InventarioService,
    public ventaController: VentaController,
    public sucursalController: SucursalController,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    public posIndexedDb: PosIndexedDbService,
    private cobroOfflineService: CobroOfflineService
  ) {}

  ngOnInit(): void {
    // 1. Inicializar detección de conectividad del navegador
    this.iniciarListenersRed();

    // 2. Contar ventas pendientes de sincronizar en IndexedDB
    this.actualizarContadorPendientes();

    // 3. Cargar Sucursales (con respaldo en IndexedDB)
    this.sucursalController.sucursales$.pipe(takeUntil(this.destroy$)).subscribe(sucursales => {
      if (sucursales && sucursales.length > 0) {
        this.sucursales = sucursales;
        this.posIndexedDb.guardarSucursales(sucursales);
        const idToSet = this.sucursalControl.value || sucursales[0].id;
        this.sucursalControl.setValue(idToSet, { emitEvent: false });
        this.cargarInventarioSucursal(idToSet);
      }
    });

    // 4. Cargar Métodos de Pago (con respaldo en IndexedDB)
    this.ventaController.metodosPago$.pipe(takeUntil(this.destroy$)).subscribe(metodos => {
      if (metodos && metodos.length > 0) {
        const filtrados = metodos.filter(m => 
          !m.nombre.toLowerCase().includes('digital') && 
          !m.nombre.toLowerCase().includes('online')
        );
        this.metodosPago = filtrados;
        this.posIndexedDb.guardarMetodosPago(filtrados);
        if (this.metodosPago.length > 0 && !this.metodoPagoControl.value) {
          const efectivo = this.metodosPago.find(m => m.nombre.toLowerCase().includes('efectivo')) || this.metodosPago[0];
          this.metodoPagoControl.setValue(efectivo.id);
        }
      }
    });

    // 5. Reactividad al cambiar de sucursal
    this.sucursalControl.valueChanges
      .pipe(distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(sucursalId => {
        if (sucursalId) {
          this.cargarInventarioSucursal(sucursalId);
          this.cart = []; // Vaciar ticket si cambia de tienda
        }
      });

    // 6. Búsqueda rápida de productos
    this.searchControl.valueChanges
      .pipe(debounceTime(200), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(term => {
        this.filtrarProductos(term || '');
      });

    // Resetear confirmaciones al cambiar método de pago
    this.metodoPagoControl.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.qrConfirmadoManual = false;
      });

    this.cargarDatosIniciales();

    // 7. Timer periódico de sincronización automática en segundo plano (cada 20s)
    this.autoSyncInterval = setInterval(() => {
      if (this.isOnline && !this.modoOfflineForzado && this.ventasPendientesSyncCount > 0 && !this.sincronizandoVentas) {
        this.sincronizarVentasPendientes(true);
      }
    }, 20000);
  }

  ngOnDestroy(): void {
    if (this.autoSyncInterval) {
      clearInterval(this.autoSyncInterval);
    }
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ============================================================================
  // MONITOREO DE RED & INDEXEDDB
  // ============================================================================

  private handleOnline = () => {
    this.isOnline = true;
    this.snackBar.open('🟢 Conexión a internet reestablecida. Verificando sincronización a la nube...', 'OK', { duration: 3500 });
    this.actualizarContadorPendientes();
    if (this.ventasPendientesSyncCount > 0) {
      this.sincronizarVentasPendientes(false);
    }
  };

  private handleOffline = () => {
    this.isOnline = false;
    this.snackBar.open('🟠 Sin conexión a internet. El POS ha cambiado a modo Contingencia Offline (IndexedDB activo).', 'Entendido', { duration: 5000 });
  };

  private iniciarListenersRed(): void {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline);
      window.addEventListener('offline', this.handleOffline);
    }
  }

  async actualizarContadorPendientes(): Promise<void> {
    try {
      this.ventasPendientesSyncCount = await this.posIndexedDb.contarVentasPendientes();
    } catch (e) {
      console.error('Error contando ventas pendientes en IndexedDB:', e);
    }
  }

  toggleModoOffline(forzar?: boolean): void {
    this.modoOfflineForzado = forzar !== undefined ? forzar : !this.modoOfflineForzado;
    if (this.modoOfflineForzado) {
      this.snackBar.open('Modo Contingencia Offline FORZADO: Todas las ventas se resguardarán en IndexedDB del navegador.', 'OK', { duration: 4000 });
    } else {
      this.snackBar.open('Modo Normal Restaurado: Conexión con servidor central en la nube activada.', 'OK', { duration: 3000 });
      if (this.isOnline && this.ventasPendientesSyncCount > 0) {
        this.sincronizarVentasPendientes(false);
      }
    }
    const currentSucursal = this.sucursalControl.value;
    if (currentSucursal) {
      this.cargarInventarioSucursal(currentSucursal);
    }
  }

  private async cargarDatosIniciales(): Promise<void> {
    // Si estamos sin red o se produce un error, restaurar desde IndexedDB
    try {
      this.sucursalController.loadSucursales();
    } catch {
      const sucsLocales = await this.posIndexedDb.obtenerSucursales();
      if (sucsLocales.length > 0) {
        this.sucursales = sucsLocales;
        this.sucursalControl.setValue(sucsLocales[0].id, { emitEvent: false });
        this.cargarInventarioDesdeIndexedDb(sucsLocales[0].id);
      }
    }

    try {
      this.ventaController.loadMetodosPago();
    } catch {
      const metodosLocales = await this.posIndexedDb.obtenerMetodosPago();
      if (metodosLocales.length > 0) {
        this.metodosPago = metodosLocales;
        this.metodoPagoControl.setValue(metodosLocales[0].id);
      }
    }
  }

  // ============================================================================
  // CARGA DE INVENTARIO (ONLINE + INDEXEDDB OFFLINE FIRST)
  // ============================================================================

  cargarInventarioSucursal(sucursalId: number): void {
    this.loading = true;

    // Si no hay internet o está forzado el modo contingencia, cargar desde IndexedDB
    if (!this.isOnline || this.modoOfflineForzado) {
      this.cargarInventarioDesdeIndexedDb(sucursalId);
      return;
    }

    // Modo Online: Consultar API central en la nube y sincronizar a IndexedDB
    this.inventarioService.getInventario(sucursalId).subscribe({
      next: (items) => {
        const mapeados = items.map(it => ({
          ...it,
          talla: it.talla || it.talla_nombre || 'Única',
          color: it.color || it.color_nombre || 'Estándar',
          imagen_url: it.imagen_url || ''
        }));
        this.productosCatalogo = mapeados;
        this.filtrarProductos(this.searchControl.value || '');
        this.loading = false;

        // Resguardo asíncrono en IndexedDB del navegador
        this.posIndexedDb.guardarCatalogoSucursal(sucursalId, mapeados).catch(err => {
          console.warn('Aviso al guardar catálogo en IndexedDB:', err);
        });
      },
      error: async (err: any) => {
        console.warn('Fallo al consultar inventario central, recurriendo a IndexedDB local:', err);
        await this.cargarInventarioDesdeIndexedDb(sucursalId);
      }
    });
  }

  async cargarInventarioDesdeIndexedDb(sucursalId: number): Promise<void> {
    this.loading = true;
    try {
      const itemsLocales = await this.posIndexedDb.obtenerCatalogoSucursal(sucursalId);
      if (itemsLocales.length > 0) {
        this.productosCatalogo = itemsLocales;
        this.filtrarProductos(this.searchControl.value || '');
        this.snackBar.open('Mostrando catálogo local desde IndexedDB (Modo Offline)', 'OK', { duration: 2500 });
      } else {
        this.productosCatalogo = [];
        this.productosFiltrados = [];
        this.snackBar.open('No hay productos guardados en la memoria local IndexedDB de esta sucursal. Conéctese a internet para precargar el catálogo.', 'Cerrar', { duration: 4000 });
      }
    } catch (e) {
      console.error('Error leyendo catálogo de IndexedDB:', e);
    } finally {
      this.loading = false;
    }
  }

  filtrarProductos(term: string): void {
    const q = term.toLowerCase().trim();
    if (!q) {
      this.productosFiltrados = [...this.productosCatalogo];
    } else {
      this.productosFiltrados = this.productosCatalogo.filter(p =>
        p.producto_nombre.toLowerCase().includes(q) ||
        (p.color ? p.color.toLowerCase().includes(q) : false) ||
        (p.talla ? p.talla.toLowerCase().includes(q) : false) ||
        (p.sku ? p.sku.toLowerCase().includes(q) : false)
      );
    }
  }

  // ============================================================================
  // OPERACIONES DEL CARRITO
  // ============================================================================

  getStockDisponible(item: InventarioItem): number {
    if (item.stockdisponible !== undefined) {
      return item.stockdisponible;
    }
    return Math.max(0, item.stockfisico - (item.stockreservado || 0));
  }

  addToCart(item: InventarioItem): void {
    const stockDisp = this.getStockDisponible(item);
    if (stockDisp <= 0) {
      const msg = (item.stockreservado || 0) > 0
        ? `Prenda reservada: ${item.producto_nombre} tiene unidades físicas pero están apartadas en reservas pendientes.`
        : `¡Sin existencias de ${item.producto_nombre}!`;
      this.snackBar.open(msg, 'Cerrar', { duration: 3000 });
      return;
    }

    const existing = this.cart.find(c => c.inventarioItem.id === item.id);
    if (existing) {
      if (existing.cantidad + 1 > stockDisp) {
        this.snackBar.open(`Stock máximo disponible para venta alcanzado (${stockDisp} un.)`, 'Cerrar', { duration: 2500 });
        return;
      }
      existing.cantidad += 1;
      existing.subtotal = existing.cantidad * existing.precioUnitario;
    } else {
      const precioUnit = item.producto_precio ? Number(item.producto_precio) : 85.00;
      this.cart.push({
        inventarioItem: item,
        cantidad: 1,
        precioUnitario: precioUnit,
        subtotal: precioUnit
      });
    }

    this.snackBar.open(`Agregado al ticket: ${item.producto_nombre} (${item.talla})`, 'OK', { duration: 1200 });
  }

  incrementQty(cartItem: PosCartItem): void {
    const stockDisp = this.getStockDisponible(cartItem.inventarioItem);
    if (cartItem.cantidad + 1 > stockDisp) {
      this.snackBar.open(`Stock disponible para venta: ${stockDisp} un.`, 'OK', { duration: 2000 });
      return;
    }
    cartItem.cantidad += 1;
    cartItem.subtotal = cartItem.cantidad * cartItem.precioUnitario;
  }

  decrementQty(cartItem: PosCartItem): void {
    if (cartItem.cantidad > 1) {
      cartItem.cantidad -= 1;
      cartItem.subtotal = cartItem.cantidad * cartItem.precioUnitario;
    } else {
      this.removeItem(cartItem);
    }
  }

  removeItem(cartItem: PosCartItem): void {
    this.cart = this.cart.filter(c => c !== cartItem);
  }

  clearCart(): void {
    this.cart = [];
    this.montoRecibidoControl.setValue(null);
    this.qrConfirmadoManual = false;
  }

  // --- Totales ---
  get subtotal(): number {
    return this.cart.reduce((acc, it) => acc + it.subtotal, 0);
  }

  get total(): number {
    return this.subtotal;
  }

  get cambio(): number {
    const recibido = Number(this.montoRecibidoControl.value || 0);
    if (recibido >= this.total && this.total > 0) {
      return recibido - this.total;
    }
    return 0;
  }

  setMontoRapido(monto: number): void {
    this.montoRecibidoControl.setValue(monto);
  }

  get metodoSeleccionado(): MetodoPago | undefined {
    return this.metodosPago.find(m => m.id === this.metodoPagoControl.value);
  }

  get esEfectivo(): boolean {
    return !!this.metodoSeleccionado?.nombre.toLowerCase().includes('efectivo');
  }

  get esQR(): boolean {
    const n = this.metodoSeleccionado?.nombre.toLowerCase() || '';
    return n.includes('qr') || n.includes('transferencia');
  }

  get esTarjeta(): boolean {
    const n = this.metodoSeleccionado?.nombre.toLowerCase() || '';
    return n.includes('tarjeta') || n.includes('crédito') || n.includes('débito') || n.includes('visa');
  }

  // ============================================================================
  // PROCESAMIENTO DE COBRO (ONLINE O EN CONTINGENCIA INDEXEDDB)
  // ============================================================================

  procesarCobro(): void {
    if (this.cart.length === 0) {
      this.snackBar.open('El ticket de venta está vacío', 'Cerrar', { duration: 3000 });
      return;
    }

    const sucursalId = this.sucursalControl.value;
    const metodoPagoId = this.metodoPagoControl.value;

    if (!sucursalId || !metodoPagoId) {
      this.snackBar.open('Seleccione una sucursal y una forma de pago válidas', 'Cerrar', { duration: 3000 });
      return;
    }

    // Validación Efectivo
    if (this.esEfectivo) {
      const montoRecibido = Number(this.montoRecibidoControl.value || 0);
      if (montoRecibido < this.total) {
        this.snackBar.open(`El monto en efectivo (Bs. ${montoRecibido.toFixed(2)}) es menor al total a cobrar (Bs. ${this.total.toFixed(2)})`, 'Cerrar', { duration: 3500 });
        return;
      }
      this.ejecutarRegistroVenta(sucursalId, metodoPagoId, montoRecibido);
      return;
    }

    // Validación QR con confirmación manual del cajero
    if (this.esQR) {
      if (!this.qrConfirmadoManual) {
        this.snackBar.open('Debe marcar la casilla de confirmación de pago QR verificado en cuenta.', 'Atención', { duration: 4000 });
        return;
      }
      this.ejecutarRegistroVenta(sucursalId, metodoPagoId, this.total);
      return;
    }

    // Tarjeta
    if (this.esTarjeta) {
      if (!this.tarjetaNumero || this.tarjetaNumero.trim().length < 10) {
        this.snackBar.open('Por favor ingrese los datos de la tarjeta para procesar.', 'Cerrar', { duration: 3000 });
        return;
      }

      this.procesandoTarjeta = true;
      this.procesandoVenta = true;
      setTimeout(() => {
        this.procesandoTarjeta = false;
        this.ejecutarRegistroVenta(sucursalId, metodoPagoId, this.total);
      }, 1200);
      return;
    }

    this.ejecutarRegistroVenta(sucursalId, metodoPagoId, this.total);
  }

  private ejecutarRegistroVenta(sucursalId: number, metodoPagoId: number, montoRecibido: number): void {
    // Si estamos desconectados o en modo contingencia offline, guardar directamente en IndexedDB
    if (!this.isOnline || this.modoOfflineForzado) {
      this.guardarVentaEnIndexedDb(sucursalId, metodoPagoId, montoRecibido);
      return;
    }

    // Modo Online: intentar enviar directamente a la nube
    const dto: VentaPresencialCreateDTO = {
      sucursal_id: sucursalId,
      cliente_nombre: this.clienteNombreControl.value || 'Consumidor Final',
      metodo_pago_id: metodoPagoId,
      monto_recibido: montoRecibido,
      items: this.cart.map(c => ({
        producto_id: c.inventarioItem.producto_id,
        cantidad: c.cantidad,
        variante_id: c.inventarioItem.variante_id
      }))
    };

    this.procesandoVenta = true;
    this.ventaController.registrarVentaPresencial(dto).subscribe({
      next: (ventaCreada) => {
        this.procesandoVenta = false;
        
        // Abrir diálogo de comprobante / ticket
        this.dialog.open(ReceiptDialogComponent, {
          width: '520px',
          data: {
            venta: ventaCreada,
            items: this.cart.map(c => ({
              nombre: c.inventarioItem.producto_nombre,
              variante: `Talla: ${c.inventarioItem.talla} | Color: ${c.inventarioItem.color}`,
              cantidad: c.cantidad,
              precio: c.precioUnitario,
              subtotal: c.subtotal
            })),
            montoRecibido: this.esEfectivo ? montoRecibido : this.total,
            cambio: this.esEfectivo ? this.cambio : 0
          }
        });

        this.clearCart();
        this.cargarInventarioSucursal(sucursalId);
        this.snackBar.open('¡Venta presencial registrada y stock descontado exitosamente en la nube!', 'Excelente', { duration: 4000 });
      },
      error: (err: any) => {
        this.procesandoVenta = false;
        // Si el fallo es por desconexión de red o caída del servidor, salvar en IndexedDB automáticamente
        if (!navigator.onLine || err.status === 0 || err.status >= 500) {
          this.snackBar.open('Pérdida de conexión con la nube. Guardando venta localmente en IndexedDB...', 'Contingencia', { duration: 3500 });
          this.guardarVentaEnIndexedDb(sucursalId, metodoPagoId, montoRecibido);
        } else {
          const msg = err.error?.detail || 'Error al procesar la venta en caja';
          this.snackBar.open(`Error: ${msg}`, 'Cerrar', { duration: 5000 });
        }
      }
    });
  }

  // ============================================================================
  // GUARDADO DE VENTA EN INDEXEDDB (CONTINGENCIA SIN INTERNET)
  // ============================================================================

  private async guardarVentaEnIndexedDb(sucursalId: number, metodoPagoId: number, montoRecibido: number): Promise<void> {
    try {
      this.procesandoVenta = true;
      const sucursalObj = this.sucursales.find(s => s.id === sucursalId);
      const metodoObj = this.metodosPago.find(m => m.id === metodoPagoId);

      // Generar Folio Provisional de Contingencia (ej. REC-POS-8Y3K21)
      const caracteres = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
      let sufijo = '';
      for (let i = 0; i < 6; i++) {
        sufijo += caracteres.charAt(Math.floor(Math.random() * caracteres.length));
      }
      const folioProvisional = `REC-POS-${sufijo}`;
      const uuid = (typeof window !== 'undefined' && window.crypto && window.crypto.randomUUID)
        ? window.crypto.randomUUID()
        : `off-pos-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

      const itemsSnapshot = this.cart.map(c => ({
        variante_id: c.inventarioItem.variante_id,
        producto_id: c.inventarioItem.producto_id,
        producto_nombre: c.inventarioItem.producto_nombre,
        talla: c.inventarioItem.talla,
        color: c.inventarioItem.color,
        cantidad: c.cantidad,
        precio_unitario: c.precioUnitario,
        subtotal: c.subtotal,
        inventarioId: c.inventarioItem.id
      }));

      // Descontar inventario en IndexedDB localmente para evitar sobreventa en modo offline
      await this.posIndexedDb.descontarStockLocal(
        sucursalId,
        itemsSnapshot.map(it => ({ inventarioId: it.inventarioId, varianteId: it.variante_id, cantidad: it.cantidad }))
      );

      // Actualizar también el estado en memoria para que la UI refleje el nuevo stock
      for (const it of itemsSnapshot) {
        const prod = this.productosCatalogo.find(p => p.id === it.inventarioId);
        if (prod) {
          prod.stockfisico = Math.max(0, prod.stockfisico - it.cantidad);
          if (prod.stockdisponible !== undefined) {
            prod.stockdisponible = Math.max(0, prod.stockdisponible - it.cantidad);
          }
        }
      }
      this.filtrarProductos(this.searchControl.value || '');

      const ahora = new Date().toISOString();

      // Registro formal para IndexedDB
      const ventaOffline: VentaOfflineRecord = {
        nro_recibo_provisional: folioProvisional,
        uuid_operacion: uuid,
        sucursal_id: sucursalId,
        sucursal_nombre: sucursalObj?.nombre || 'Sucursal Mostrador',
        cliente_nombre: this.clienteNombreControl.value || 'Consumidor Final',
        cliente_nit: this.clienteNitControl.value || '0',
        monto: this.total,
        moneda: 'BOB',
        metodo_pago_id: metodoPagoId,
        metodo_pago_nombre: metodoObj?.nombre || 'Efectivo',
        efectivo_recibido: this.esEfectivo ? montoRecibido : this.total,
        cambio: this.esEfectivo ? this.cambio : 0,
        observaciones: `[VENTA POS CONTINGENCIA OFFLINE EN NAVEGADOR] Folio: ${folioProvisional}`,
        fecha_cobro: ahora,
        sincronizado: false,
        items: itemsSnapshot
      };

      await this.posIndexedDb.guardarVentaOffline(ventaOffline);
      await this.actualizarContadorPendientes();

      // Construir VentaCompleta simulada para abrir el diálogo del comprobante / ticket
      const ventaModal: VentaCompleta = {
        id: Date.now(),
        codigoventa: folioProvisional,
        tipoventa: 'Presencial (Offline Contingencia)',
        estado: 'PROVISIONAL_OFFLINE',
        subtotal: this.subtotal,
        descuento: 0,
        total: this.total,
        fecha: ahora,
        sucursalid: sucursalId,
        sucursal_nombre: sucursalObj?.nombre || 'Sucursal Mostrador',
        cliente_nombre: this.clienteNombreControl.value || 'Consumidor Final',
        metodo_pago_nombre: metodoObj?.nombre || 'Efectivo',
        cambio: this.esEfectivo ? this.cambio : 0
      };

      this.dialog.open(ReceiptDialogComponent, {
        width: '520px',
        data: {
          venta: ventaModal,
          items: itemsSnapshot.map(c => ({
            nombre: c.producto_nombre,
            variante: `Talla: ${c.talla} | Color: ${c.color}`,
            cantidad: c.cantidad,
            precio: c.precio_unitario,
            subtotal: c.subtotal
          })),
          montoRecibido: this.esEfectivo ? montoRecibido : this.total,
          cambio: this.esEfectivo ? this.cambio : 0
        }
      });

      this.clearCart();
      this.snackBar.open(
        `¡Venta ${folioProvisional} guardada en IndexedDB del navegador! Se sincronizará automáticamente al volver internet.`,
        'Entendido',
        { duration: 6000 }
      );
    } catch (e) {
      console.error('Error guardando venta offline en IndexedDB:', e);
      this.snackBar.open(`Error al resguardar venta offline: ${e}`, 'Cerrar', { duration: 5000 });
    } finally {
      this.procesandoVenta = false;
    }
  }

  // ============================================================================
  // SINCRONIZACIÓN DE VENTAS DE INDEXEDDB A LA NUBE
  // ============================================================================

  async sincronizarVentasPendientes(silencioso: boolean = false): Promise<void> {
    if (this.sincronizandoVentas) return;

    const pendientes = await this.posIndexedDb.obtenerVentasPendientes();
    if (pendientes.length === 0) {
      this.ventasPendientesSyncCount = 0;
      if (!silencioso) {
        this.snackBar.open('No hay ventas offline pendientes en IndexedDB. Todo sincronizado en la nube.', 'OK', { duration: 3000 });
      }
      return;
    }

    if (!this.isOnline) {
      if (!silencioso) {
        this.snackBar.open('Sin conexión a internet. Las ventas permanecen resguardadas en IndexedDB.', 'Cerrar', { duration: 3500 });
      }
      return;
    }

    this.sincronizandoVentas = true;
    if (!silencioso) {
      this.snackBar.open(`Sincronizando ${pendientes.length} venta(s) offline con la nube...`, '', { duration: 2500 });
    }

    try {
      // Mapear al DTO esperado por el endpoint /api/v1/cobros-offline/lote
      const payload: RegistroCobroOfflineRequest[] = pendientes.map(p => ({
        sucursal_id: p.sucursal_id,
        monto: p.monto,
        moneda: p.moneda || 'BOB',
        nro_recibo_provisional: p.nro_recibo_provisional,
        uuid_operacion: p.uuid_operacion,
        cliente_nombre: p.cliente_nombre,
        cliente_nit: p.cliente_nit || '0',
        efectivo_recibido: p.efectivo_recibido,
        cambio: p.cambio,
        observaciones: p.observaciones || 'Venta POS Offline resguardada en IndexedDB',
        fecha_cobro: p.fecha_cobro,
        items: p.items.map(it => ({
          variante_id: it.variante_id,
          producto_nombre: it.producto_nombre,
          talla: it.talla || 'M',
          color: it.color || 'Estándar',
          cantidad: it.cantidad,
          precio_unitario: it.precio_unitario,
          subtotal: it.subtotal
        }))
      }));

      this.cobroOfflineService.subirLote(payload).subscribe({
        next: async (res) => {
          if (res.exito) {
            const foliosMap = pendientes.map(p => ({
              nro_recibo_provisional: p.nro_recibo_provisional
            }));

            await this.posIndexedDb.marcarVentasSincronizadas(foliosMap);
            await this.actualizarContadorPendientes();
            this.sincronizandoVentas = false;

            this.snackBar.open(
              `¡${pendientes.length} venta(s) offline sincronizada(s) exitosamente con la base de datos central en la nube!`,
              'Excelente',
              { duration: 5000 }
            );

            // Refrescar inventario fresco desde la nube
            const sucursalId = this.sucursalControl.value;
            if (sucursalId) {
              this.cargarInventarioSucursal(sucursalId);
            }
          }
        },
        error: (err) => {
          console.error('Error al subir lote a la nube:', err);
          this.sincronizandoVentas = false;
          if (!silencioso) {
            this.snackBar.open('No se pudo conectar con el servidor central. Las ventas siguen seguras en IndexedDB.', 'Cerrar', { duration: 4000 });
          }
        }
      });
    } catch (e) {
      console.error('Excepción al sincronizar lote:', e);
      this.sincronizandoVentas = false;
    }
  }
}
