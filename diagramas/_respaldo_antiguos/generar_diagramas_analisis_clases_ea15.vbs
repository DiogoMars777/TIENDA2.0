option explicit

!INC Local Scripts.EAConstants-VBScript

' =====================================================================
' Script: Generar Diagramas de Análisis de Clases (Boundary - Control - Entity)
' Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
' Herramienta: Enterprise Architect 15 / 16
' Descripción: Genera EXCLUSIVAMENTE los diagramas de clases de análisis
'              para los 14 Casos de Uso implementados en el proyecto:
'              CU01, CU02, CU03, CU04, CU05, CU06, CU07, CU08, CU09,
'              CU10, CU11, CU13, CU14 y CU15.
' =====================================================================

sub OnDiagramScript()
    dim currentPackage
    set currentPackage = Repository.GetTreeSelectedPackage()
    
    if currentPackage is nothing then
        Session.Prompt "Por favor, selecciona un Paquete en el Project Browser antes de ejecutar.", promptOK
        exit sub
    end if

    ' Definir los 14 Casos de Uso implementados en el sistema
    dim casosUso
    casosUso = Array( _
        getCU01(), _
        getCU02(), _
        getCU03(), _
        getCU04(), _
        getCU05(), _
        getCU06(), _
        getCU07(), _
        getCU08(), _
        getCU09(), _
        getCU10(), _
        getCU11(), _
        getCU13(), _
        getCU14(), _
        getCU15() _
    )

    dim i, cu, nombreActor, metodosActor, clases, nombreDiagrama
    for i = 0 to UBound(casosUso)
        cu = casosUso(i)
        nombreActor = cu(0)
        metodosActor = cu(1)
        clases = cu(2)
        nombreDiagrama = "Análisis " & cu(3)

        crearDiagramaCasoUso currentPackage, nombreActor, metodosActor, clases, nombreDiagrama
    next

    Repository.RefreshModelView(0)
    Session.Prompt "¡Se generaron exitosamente los " & (UBound(casosUso) + 1) & " diagramas de análisis de clases del proyecto (CU01 al CU15)!", promptOK
end sub

' =============================================================
' FUNCIONES PARA CADA CASO DE USO DEL PROYECTO
' =============================================================

function getCU01()
    ' CU01: Gestionar Autenticación y Recuperación
    dim metodosActor, clases
    metodosActor = Array("+ ingresarCredenciales(): void", "+ enviarLogin(): void", "+ solicitarRecuperacion(): void", "+ restablecerPassword(): void")
    
    clases = Array( _
        Array( _
            "CU01 Autenticación: UI_Auth", _
            Array("- loginForm: Form", "- recoverForm: Form", "- inputEmail: string", "- inputPassword: string"), _
            Array("+ mostrarLogin(): void", "+ enviarCredenciales(): void", "+ mostrarRecuperar(): void", "+ mostrarMensaje(): void") _
        ), _
        Array( _
            "CU01 Autenticación: AuthController", _
            Array("- authService: AuthService", "- jwtManager: JWTManager", "- emailService: EmailService"), _
            Array("+ login_user(email, password): TokenResponse", "+ request_password_recovery(email): void", "+ reset_password(token, newPass): void", "+ verify_otp_code(email, code): boolean") _
        ), _
        Array( _
            "CU01 Autenticación: Usuario", _
            Array("- id: int", "- nombre: string", "- apellido: string", "- email: string", "- passwordHash: string", "- rolId: int", "- activo: boolean"), _
            Array("+ buscarPorEmail(email): Usuario", "+ verificarPassword(pass): boolean", "+ actualizarPassword(hash): void") _
        ), _
        Array( _
            "CU01 Autenticación: Rol", _
            Array("- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"), _
            Array("+ obtenerPermisos(): List<string>") _
        ) _
    )
    getCU01 = Array("Cliente", metodosActor, clases, "CU01 - Gestionar Autenticacion")
end function

function getCU02()
    ' CU02: Gestionar Usuarios y Roles
    dim metodosActor, clases
    metodosActor = Array("+ listarUsuarios(): void", "+ crearUsuario(): void", "+ editarUsuario(): void", "+ asignarRol(): void")
    
    clases = Array( _
        Array( _
            "CU02 Usuarios y Roles: UI_UserRole", _
            Array("- tablaUsuarios: DataTable", "- modalUsuario: FormModal", "- selectorRol: Dropdown"), _
            Array("+ mostrarUsuarios(): void", "+ abrirModalCrear(): void", "+ guardarUsuario(): void", "+ cambiarEstadoActivo(): void") _
        ), _
        Array( _
            "CU02 Usuarios y Roles: UserController", _
            Array("- userService: UserService", "- roleController: RoleController"), _
            Array("+ get_all(): List<Usuario>", "+ create_user(datos): Usuario", "+ update_user(id, datos): Usuario", "+ toggle_active(id): void") _
        ), _
        Array( _
            "CU02 Usuarios y Roles: Usuario", _
            Array("- id: int", "- nombre: string", "- apellido: string", "- email: string", "- rolId: int", "- sucursalId: int", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void", "+ cambiarEstado(activo): void") _
        ), _
        Array( _
            "CU02 Usuarios y Roles: Rol", _
            Array("- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"), _
            Array("+ crear(): void", "+ listarRoles(): List<Rol>") _
        ) _
    )
    getCU02 = Array("Administrador", metodosActor, clases, "CU02 - Gestionar Usuarios y Roles")
end function

function getCU03()
    ' CU03: Gestionar Clientes
    dim metodosActor, clases
    metodosActor = Array("+ verListaClientes(): void", "+ crearCliente(): void", "+ actualizarCliente(): void")
    
    clases = Array( _
        Array( _
            "CU03 Clientes: UI_Cliente", _
            Array("- tablaClientes: DataTable", "- formCliente: FormModal", "- buscadorInput: string"), _
            Array("+ mostrarClientes(): void", "+ cargarDatosCliente(): void", "+ guardarCliente(): void") _
        ), _
        Array( _
            "CU03 Clientes: ClienteController", _
            Array("- clienteService: ClienteService"), _
            Array("+ listar_clientes(search): List<Cliente>", "+ obtener_cliente(id): Cliente", "+ crear_cliente(datos): Cliente", "+ actualizar_cliente(id, datos): Cliente") _
        ), _
        Array( _
            "CU03 Clientes: Cliente", _
            Array("- id: int", "- usuarioId: int", "- nitCi: string", "- telefono: string", "- direccion: string", "- fechaRegistro: DateTime"), _
            Array("+ crear(): void", "+ actualizar(): void", "+ obtenerHistorialCompras(): List<Venta>") _
        ), _
        Array( _
            "CU03 Clientes: Usuario", _
            Array("- id: int", "- nombre: string", "- apellido: string", "- email: string"), _
            Array("+ getDatosBasicos(): Usuario") _
        ) _
    )
    getCU03 = Array("Administrador", metodosActor, clases, "CU03 - Gestionar Clientes")
end function

function getCU04()
    ' CU04: Gestionar Sucursales
    dim metodosActor, clases
    metodosActor = Array("+ verSucursales(): void", "+ registrarSucursal(): void", "+ editarSucursal(): void")
    
    clases = Array( _
        Array( _
            "CU04 Sucursales: UI_Sucursal", _
            Array("- tablaSucursales: DataTable", "- formSucursal: FormModal"), _
            Array("+ mostrarSucursales(): void", "+ abrirFormulario(): void", "+ guardarSucursal(): void") _
        ), _
        Array( _
            "CU04 Sucursales: SucursalController", _
            Array("- sucursalService: SucursalService"), _
            Array("+ listar_sucursales(search, ciudad): List<Sucursal>", "+ crear_sucursal(datos): Sucursal", "+ actualizar_sucursal(id, datos): Sucursal", "+ baja_logica(id): void") _
        ), _
        Array( _
            "CU04 Sucursales: Sucursal", _
            Array("- id: int", "- nombre: string", "- ciudad: string", "- direccion: string", "- telefono: string", "- latitud: decimal", "- longitud: decimal", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void", "+ cambiarEstado(activo): void") _
        ) _
    )
    getCU04 = Array("Administrador", metodosActor, clases, "CU04 - Gestionar Sucursales")
end function

function getCU05()
    ' CU05: Gestionar Productos (Poleras)
    dim metodosActor, clases
    metodosActor = Array("+ verProductosAdmin(): void", "+ crearPolera(): void", "+ editarPolera(): void", "+ gestionarVariantes(): void")
    
    clases = Array( _
        Array( _
            "CU05 Productos: UI_Producto", _
            Array("- tablaProductos: DataTable", "- modalProducto: FormModal", "- gridVariantes: SubGrid"), _
            Array("+ mostrarProductos(): void", "+ abrirCrearProducto(): void", "+ guardarProducto(): void", "+ configurarVariantes(): void") _
        ), _
        Array( _
            "CU05 Productos: ProductoController", _
            Array("- productoService: ProductoService"), _
            Array("+ listar_productos(search, catId): List<Producto>", "+ crear_producto(datos): Producto", "+ actualizar_producto(id, datos): Producto", "+ crear_variante(prodId, varData): Variante") _
        ), _
        Array( _
            "CU05 Productos: Producto", _
            Array("- id: int", "- nombre: string", "- descripcion: string", "- precioBase: decimal", "- categoriaId: int", "- imagenPrincipal: string", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void", "+ bajaLogica(): void") _
        ), _
        Array( _
            "CU05 Productos: VarianteProducto", _
            Array("- id: int", "- productoId: int", "- colorId: int", "- tallaId: int", "- sku: string", "- precioVenta: decimal"), _
            Array("+ crear(): void", "+ actualizarPrecio(): void") _
        ) _
    )
    getCU05 = Array("Administrador", metodosActor, clases, "CU05 - Gestionar Productos")
end function

function getCU06()
    ' CU06: Gestionar Clasificación de Prendas
    dim metodosActor, clases
    metodosActor = Array("+ verCategorias(): void", "+ crearCategoria(): void", "+ crearTemporada(): void", "+ crearColeccion(): void")
    
    clases = Array( _
        Array( _
            "CU06 Clasificación: UI_Clasificacion", _
            Array("- tabsClasificacion: Tabs", "- tablaCategorias: Table", "- tablaTemporadas: Table", "- tablaColecciones: Table"), _
            Array("+ mostrarCategorias(): void", "+ mostrarTemporadas(): void", "+ guardarCategoria(): void", "+ guardarTemporada(): void") _
        ), _
        Array( _
            "CU06 Clasificación: ClasificacionController", _
            Array("- clasificacionService: ClasificacionService"), _
            Array("+ listar_categorias(): List<Categoria>", "+ crear_categoria(datos): Categoria", "+ listar_temporadas(): List<Temporada>", "+ crear_temporada(datos): Temporada", "+ listar_colecciones(): List<Coleccion>") _
        ), _
        Array( _
            "CU06 Clasificación: Categoria", _
            Array("- id: int", "- nombre: string", "- descripcion: string", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void") _
        ), _
        Array( _
            "CU06 Clasificación: Temporada", _
            Array("- id: int", "- nombre: string", "- fechaInicio: Date", "- fechaFin: Date", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void") _
        ), _
        Array( _
            "CU06 Clasificación: Coleccion", _
            Array("- id: int", "- nombre: string", "- temporadaId: int", "- activo: boolean"), _
            Array("+ crear(): void") _
        ) _
    )
    getCU06 = Array("Administrador", metodosActor, clases, "CU06 - Gestionar Clasificacion de Prendas")
end function

function getCU07()
    ' CU07: Gestionar Proveedores y Suministros
    dim metodosActor, clases
    metodosActor = Array("+ verProveedores(): void", "+ registrarProveedor(): void", "+ vincularSuministro(): void")
    
    clases = Array( _
        Array( _
            "CU07 Proveedores: UI_Proveedor", _
            Array("- tablaProveedores: Table", "- modalProveedor: FormModal", "- panelSuministros: SubTable"), _
            Array("+ mostrarProveedores(): void", "+ nuevoProveedor(): void", "+ guardarProveedor(): void", "+ vincularProducto(): void") _
        ), _
        Array( _
            "CU07 Proveedores: ProveedorController", _
            Array("- proveedorService: ProveedorService"), _
            Array("+ listar_proveedores(): List<Proveedor>", "+ crear_proveedor(datos): Proveedor", "+ actualizar_proveedor(id, datos): Proveedor", "+ vincular_producto(provId, prodId, costo, cant): void") _
        ), _
        Array( _
            "CU07 Proveedores: Proveedor", _
            Array("- id: int", "- nombre: string", "- razonSocial: string", "- nit: string", "- contacto: string", "- telefono: string", "- activo: boolean"), _
            Array("+ crear(): void", "+ actualizar(): void", "+ bajaLogica(): void") _
        ), _
        Array( _
            "CU07 Proveedores: ProductoProveedor", _
            Array("- idProducto: int", "- idProveedor: int", "- costoCompra: decimal", "- cantidad: int"), _
            Array("+ vincular(): void") _
        ) _
    )
    getCU07 = Array("Administrador", metodosActor, clases, "CU07 - Gestionar Proveedores y Suministros")
end function

function getCU08()
    ' CU08: Consultar Catálogo y Disponibilidad Multitienda
    dim metodosActor, clases
    metodosActor = Array("+ navegarCatalogo(): void", "+ seleccionarSucursal(): void", "+ filtrarTallaColor(): void", "+ verDetallePrenda(): void")
    
    clases = Array( _
        Array( _
            "CU08 Catálogo: UI_Catalogo", _
            Array("- gridPoleras: List<Card>", "- selectorSucursal: Dropdown", "- chipsTallas: ChipGroup", "- buscadorTexto: string"), _
            Array("+ mostrarCatalogo(): void", "+ filtrarPorSucursal(): void", "+ seleccionarTallaColor(): void", "+ verDetalle(): void") _
        ), _
        Array( _
            "CU08 Catálogo: InventarioController", _
            Array("- catalogoService: CatalogoService", "- stockService: StockService"), _
            Array("+ listar_catalogo(sucursalId, catId, genero): List<ProductoCatalogoItem>", "+ verificar_stock_variante(varId, sucId): int") _
        ), _
        Array( _
            "CU08 Catálogo: Producto", _
            Array("- id: int", "- nombre: string", "- precioBase: decimal", "- categoriaId: int", "- imagenPrincipal: string"), _
            Array("+ listarActivos(): List<Producto>") _
        ), _
        Array( _
            "CU08 Catálogo: VarianteProducto", _
            Array("- id: int", "- productoId: int", "- colorId: int", "- tallaId: int", "- sku: string", "- precioVenta: decimal"), _
            Array("+ getDisponibilidad(): int") _
        ), _
        Array( _
            "CU08 Catálogo: Inventario", _
            Array("- id: int", "- varianteId: int", "- sucursalId: int", "- stock: int", "- stockMinimo: int"), _
            Array("+ estaDisponible(): boolean", "+ getStockSucursal(): int") _
        ) _
    )
    getCU08 = Array("Cliente", metodosActor, clases, "CU08 - Consultar Catalogo y Disponibilidad")
end function

function getCU09()
    ' CU09: Gestionar Carrito de Compras Omnicanal
    dim metodosActor, clases
    metodosActor = Array("+ verCarrito(): void", "+ agregarItem(): void", "+ modificarCantidad(): void", "+ eliminarItem(): void")
    
    clases = Array( _
        Array( _
            "CU09 Carrito: UI_Carrito", _
            Array("- itemsCarrito: List<ItemCard>", "- selectorSucursalRetiro: Dropdown", "- subtotalLabel: Label", "- btnCheckout: Button"), _
            Array("+ mostrarCarrito(): void", "+ actualizarCantidad(): void", "+ eliminarItem(): void", "+ seleccionarModalidad(): void") _
        ), _
        Array( _
            "CU09 Carrito: CarritoController", _
            Array("- carritoService: CarritoService", "- inventarioService: InventarioService"), _
            Array("+ obtener_carrito_dto(clienteId): CarritoDTO", "+ agregar_item(clienteId, varId, cant): void", "+ actualizar_item(clienteId, varId, cant): void", "+ eliminar_item(clienteId, varId): void") _
        ), _
        Array( _
            "CU09 Carrito: Carrito", _
            Array("- id: int", "- clienteId: int", "- sucursalId: int", "- estado: string", "- fechaActualizacion: DateTime"), _
            Array("+ agregarItem(): void", "+ calcularSubtotal(): decimal", "+ vaciar(): void") _
        ), _
        Array( _
            "CU09 Carrito: CarritoItem", _
            Array("- carritoId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"), _
            Array("+ calcularTotalLinea(): decimal") _
        ) _
    )
    getCU09 = Array("Cliente", metodosActor, clases, "CU09 - Gestionar Carrito de Compras")
end function

function getCU10()
    ' CU10: Gestionar Reservas de Prendas en Tienda Física
    dim metodosActor, clases
    metodosActor = Array("+ apartarPrendas(): void", "+ elegirSucursalRetiro(): void", "+ confirmarReserva(): void", "+ verMisReservas(): void", "+ cancelarReserva(): void")
    
    clases = Array( _
        Array( _
            "CU10 Reservas: UI_Reservas", _
            Array("- listaReservas: List<ReservaCard>", "- modalDetalleReserva: Modal", "- btnConfirmarReserva: Button"), _
            Array("+ mostrarMisReservas(): void", "+ verCodigoReserva(): void", "+ confirmarReserva(): void", "+ solicitarCancelacion(): void") _
        ), _
        Array( _
            "CU10 Reservas: ReservaController", _
            Array("- reservaService: ReservaService", "- inventarioController: InventarioController"), _
            Array("+ crear_reserva(clienteId, datos): Reserva", "+ listar_reservas_usuario(clienteId): List<Reserva>", "+ cancelar_reserva(reservaId, clienteId): boolean") _
        ), _
        Array( _
            "CU10 Reservas: Reserva", _
            Array("- id: int", "- codigoReserva: string", "- clienteId: int", "- sucursalId: int", "- estado: string", "- fechaCreacion: DateTime", "- fechaExpiracion: DateTime"), _
            Array("+ crear(): void", "+ cancelar(): void", "+ bloquearStock(): void") _
        ), _
        Array( _
            "CU10 Reservas: ReservaDetalle", _
            Array("- id: int", "- reservaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"), _
            Array("+ registrarItem(): void") _
        ), _
        Array( _
            "CU10 Reservas: Inventario", _
            Array("- varianteId: int", "- sucursalId: int", "- stock: int"), _
            Array("+ reservarStock(cant): void", "+ liberarStock(cant): void") _
        ) _
    )
    getCU10 = Array("Cliente", metodosActor, clases, "CU10 - Gestionar Reservas de Prendas")
end function

function getCU11()
    ' CU11: Atender Reservas en Sucursal Física (Caja / Mostrador)
    dim metodosActor, clases
    metodosActor = Array("+ consultarReservasSucursal(): void", "+ buscarCodigo(): void", "+ entregarPrendas(): void")
    
    clases = Array( _
        Array( _
            "CU11 Atender Reservas: UI_AtenderReservas", _
            Array("- inputCodigoAlfanumerico: string", "- cardDetalleReserva: Card", "- btnConfirmarEntrega: Button"), _
            Array("+ buscarCodigo(): void", "+ verificarPrendas(): void", "+ confirmarEntrega(): void", "+ cancelarPorNoRetiro(): void") _
        ), _
        Array( _
            "CU11 Atender Reservas: AtenderReservaController", _
            Array("- reservaService: ReservaService", "- inventarioService: InventarioService"), _
            Array("+ buscar_reserva_por_codigo(codigo): Reserva", "+ listar_reservas_admin(sucursalId, estado): List<Reserva>", "+ atender_reserva(reservaId, accion): Reserva") _
        ), _
        Array( _
            "CU11 Atender Reservas: Reserva", _
            Array("- id: int", "- codigoReserva: string", "- sucursalId: int", "- estado: string", "- fechaEntrega: DateTime"), _
            Array("+ marcarEntregada(): void", "+ marcarCancelada(): void") _
        ), _
        Array( _
            "CU11 Atender Reservas: Inventario", _
            Array("- varianteId: int", "- sucursalId: int", "- stock: int"), _
            Array("+ descontarFisico(cant): void") _
        ) _
    )
    getCU11 = Array("Encargado", metodosActor, clases, "CU11 - Atender Reservas en Sucursal")
end function

function getCU13()
    ' CU13: Gestionar Inventario y Movimientos (Kardex)
    dim metodosActor, clases
    metodosActor = Array("+ verExistencias(): void", "+ verKardex(): void", "+ registrarIngreso(): void", "+ registrarAjuste(): void")
    
    clases = Array( _
        Array( _
            "CU13 Inventario Kardex: UI_InventarioKardex", _
            Array("- tablaInventario: DataTable", "- tablaMovimientos: DataTable", "- modalMovimiento: FormModal"), _
            Array("+ verExistencias(): void", "+ verKardex(): void", "+ registrarIngreso(): void", "+ registrarAjuste(): void") _
        ), _
        Array( _
            "CU13 Inventario Kardex: InventarioController", _
            Array("- kardexService: KardexService"), _
            Array("+ listar_inventario(sucursalId): List<Inventario>", "+ registrar_movimiento(datosMov): MovimientoInventario", "+ ajustar_stock(varId, sucId, cant): void") _
        ), _
        Array( _
            "CU13 Inventario Kardex: Inventario", _
            Array("- id: int", "- varianteId: int", "- sucursalId: int", "- stock: int", "- stockMinimo: int"), _
            Array("+ actualizarStock(cant): void", "+ alertaStockMinimo(): boolean") _
        ), _
        Array( _
            "CU13 Inventario Kardex: MovimientoInventario", _
            Array("- id: int", "- inventarioId: int", "- tipoMovimiento: string", "- cantidad: int", "- motivoId: int", "- fecha: DateTime"), _
            Array("+ registrar(): void") _
        ) _
    )
    getCU13 = Array("Administrador", metodosActor, clases, "CU13 - Gestionar Inventario y Movimientos")
end function

function getCU14()
    ' CU14: Registrar Ventas Presenciales (Punto de Venta POS)
    dim metodosActor, clases
    metodosActor = Array("+ escanearVariante(): void", "+ seleccionarMetodoCobro(): void", "+ emitirRecibo(): void")
    
    clases = Array( _
        Array( _
            "CU14 Ventas Presenciales POS: UI_POS", _
            Array("- lectorCodigoBarra: Scanner", "- tablaLineasVenta: DataTable", "- calculadorCambio: VueltoCalc", "- selectorMetodoPago: Dropdown"), _
            Array("+ escanearVariante(): void", "+ calcularCambio(): decimal", "+ procesarCobro(): void", "+ imprimirRecibo(): void") _
        ), _
        Array( _
            "CU14 Ventas Presenciales POS: VentaPresencialController", _
            Array("- ventaService: VentaService", "- inventarioService: InventarioService", "- reciboService: ReciboService"), _
            Array("+ registrar_venta_presencial(datosVenta): Venta", "+ procesar_pago(ventaId, metodoId, monto): Pago", "+ emitir_recibo(ventaId): Recibo") _
        ), _
        Array( _
            "CU14 Ventas Presenciales POS: Venta", _
            Array("- id: int", "- sucursalId: int", "- usuarioId: int", "- clienteId: int", "- total: decimal", "- tipoVenta: string", "- estado: string"), _
            Array("+ crear(): void", "+ calcularTotales(): decimal") _
        ), _
        Array( _
            "CU14 Ventas Presenciales POS: DetalleVenta", _
            Array("- id: int", "- ventaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal", "- subtotal: decimal"), _
            Array("+ registrarLinea(): void") _
        ), _
        Array( _
            "CU14 Ventas Presenciales POS: Pago", _
            Array("- id: int", "- ventaId: int", "- metodoPagoId: int", "- monto: decimal", "- estado: string"), _
            Array("+ registrar(): void") _
        ), _
        Array( _
            "CU14 Ventas Presenciales POS: Recibo", _
            Array("- id: int", "- ventaId: int", "- numeroRecibo: string", "- fechaEmision: DateTime"), _
            Array("+ generarRecibo(): void") _
        ) _
    )
    getCU14 = Array("Cajero", metodosActor, clases, "CU14 - Registrar Ventas Presenciales (POS)")
end function

function getCU15()
    ' CU15: Realizar Compras Digitales y Seguimiento de Órdenes
    dim metodosActor, clases
    metodosActor = Array("+ realizarCheckoutOnline(): void", "+ verMisPedidos(): void", "+ verTrackingOrden(): void")
    
    clases = Array( _
        Array( _
            "CU15 Compras Digitales: UI_ComprasDigitales", _
            Array("- listaMisPedidos: List<OrderCard>", "- modalTracking: TimelineModal", "- btnDescargarRecibo: Button"), _
            Array("+ verMisPedidos(): void", "+ verTrackingOrden(): void", "+ descargarComprobante(): void") _
        ), _
        Array( _
            "CU15 Compras Digitales: CompraDigitalController", _
            Array("- ventaService: VentaService", "- carritoService: CarritoService"), _
            Array("+ realizar_compra_digital(clienteId, datosCompra): Venta", "+ listar_mis_ordenes(clienteId): List<Venta>", "+ consultar_tracking(ventaId): EstadoTrackingDTO") _
        ), _
        Array( _
            "CU15 Compras Digitales: Venta", _
            Array("- id: int", "- clienteId: int", "- total: decimal", "- tipoVenta: string", "- estado: string", "- fechaVenta: DateTime"), _
            Array("+ crearOrdenDigital(): void", "+ actualizarEstado(): void") _
        ), _
        Array( _
            "CU15 Compras Digitales: DetalleVenta", _
            Array("- id: int", "- ventaId: int", "- varianteId: int", "- cantidad: int", "- precioUnitario: decimal"), _
            Array("+ agregarItem(): void") _
        ), _
        Array( _
            "CU15 Compras Digitales: Carrito", _
            Array("- id: int", "- clienteId: int", "- estado: string"), _
            Array("+ vaciar(): void") _
        ) _
    )
    getCU15 = Array("Cliente", metodosActor, clases, "CU15 - Realizar Compras Digitales")
end function

' =============================================================
' FUNCIÓN PRINCIPAL PARA CREAR CADA DIAGRAMA DE ANÁLISIS
' =============================================================

sub crearDiagramaCasoUso(package, nombreActor, metodosActor, clases, nombreDiagrama)
    ' 1. Crear el actor con sus metodos
    dim actor
    set actor = crearElemento(package, nombreActor, "Actor")
    dim m
    for each m in metodosActor
        agregarMetodo actor, m
    next

    ' 2. Crear las clases de análisis con sus atributos y metodos
    dim claseInfo, nombreClase, atributos, metodos, claseObj
    dim listaClases
    listaClases = Array()
    
    dim cIdx
    for cIdx = 0 to UBound(clases)
        claseInfo = clases(cIdx)
        nombreClase = claseInfo(0)
        atributos = claseInfo(1)
        metodos = claseInfo(2)
        
        set claseObj = crearClase(package, nombreClase)
        dim a
        for each a in atributos
            agregarAtributo claseObj, a
        next
        for each m in metodos
            agregarMetodo claseObj, m
        next

        ' Guardar referencia para posicionar
        if UBound(listaClases) < 0 then
            ReDim listaClases(0)
        else
            ReDim Preserve listaClases(UBound(listaClases) + 1)
        end if
        set listaClases(UBound(listaClases)) = claseObj
    next

    ' 3. Crear el diagrama de clases limpio
    dim diagram
    set diagram = crearDiagramaLimpio(package, nombreDiagrama)

    ' 4. Posicionar elementos: actor a la izquierda, clases en fila horizontal
    colocarElemento diagram, actor, "50", "150", "-50", "-200"
    
    dim x, y, i, claseActual, altura
    x = 250
    y = -100
    for i = 0 to UBound(listaClases)
        set claseActual = listaClases(i)
        altura = 120 + (claseActual.Methods.Count * 20) + (claseActual.Attributes.Count * 18)
        colocarElemento diagram, claseActual, CStr(x), CStr(x + 220), CStr(y), CStr(y - altura)
        x = x + 260
    next

    ' 5. Crear asociaciones: actor -> primera clase, y entre clases secuencialmente
    if UBound(listaClases) >= 0 then
        crearAsociacion actor, listaClases(0), ""
        for i = 0 to UBound(listaClases) - 1
            crearAsociacion listaClases(i), listaClases(i + 1), ""
        next
    end if

    ' 6. Guardar y refrescar el diagrama
    Repository.SaveDiagram diagram.DiagramID
    Repository.ReloadDiagram diagram.DiagramID
    Repository.OpenDiagram diagram.DiagramID
end sub

' =============================================================
' FUNCIONES AUXILIARES (COMPATIBLES 100% CON ENTERPRISE ARCHITECT)
' =============================================================

function crearElemento(package, name, tipo)
    dim el
    for each el in package.Elements
        if el.Name = name and el.Type = tipo then
            set crearElemento = el
            exit function
        end if
    next
    set el = package.Elements.AddNew(name, tipo)
    el.Update()
    package.Elements.Refresh()
    set crearElemento = el
end function

function crearClase(package, name)
    dim el
    for each el in package.Elements
        if el.Name = name and el.Type = "Class" then
            set crearClase = el
            exit function
        end if
    next
    set el = package.Elements.AddNew(name, "Class")
    el.Update()
    package.Elements.Refresh()
    set crearClase = el
end function

sub agregarAtributo(clase, nombre)
    dim attr
    for each attr in clase.Attributes
        if attr.Name = nombre then exit sub
    next
    set attr = clase.Attributes.AddNew(nombre, "")
    attr.Update()
    clase.Attributes.Refresh()
end sub

sub agregarMetodo(elemento, nombre)
    dim method
    if elemento.Type = "Actor" then
        for each method in elemento.Methods
            if method.Name = nombre then exit sub
        next
        set method = elemento.Methods.AddNew(nombre, "")
        method.Update()
        elemento.Methods.Refresh()
    else
        for each method in elemento.Methods
            if method.Name = nombre then exit sub
        next
        set method = elemento.Methods.AddNew(nombre, "")
        method.Update()
        elemento.Methods.Refresh()
    end if
end sub

function crearDiagramaLimpio(package, name)
    dim diag, i
    for each diag in package.Diagrams
        if diag.Name = name then
            for i = diag.DiagramObjects.Count - 1 to 0 step -1
                diag.DiagramObjects.Delete i
            next
            for i = diag.DiagramLinks.Count - 1 to 0 step -1
                diag.DiagramLinks.Delete i
            next
            diag.DiagramObjects.Refresh()
            diag.DiagramLinks.Refresh()
            diag.Update()
            set crearDiagramaLimpio = diag
            exit function
        end if
    next
    set diag = package.Diagrams.AddNew(name, "Class")
    diag.Update()
    package.Diagrams.Refresh()
    set crearDiagramaLimpio = diag
end function

sub colocarElemento(diagram, elemento, left, right, top, bottom)
    dim diagObj
    set diagObj = diagram.DiagramObjects.AddNew("l=" & left & ";r=" & right & ";t=" & top & ";b=" & bottom & ";", "")
    diagObj.ElementID = elemento.ElementID
    diagObj.Update()
end sub

sub crearAsociacion(origen, destino, estereotipo)
    dim con
    for each con in origen.Connectors
        if con.SupplierID = destino.ElementID and con.Type = "Association" then
            if estereotipo = "" or con.Stereotype = estereotipo then
                exit sub
            end if
        end if
    next
    set con = origen.Connectors.AddNew("", "Association")
    con.SupplierID = destino.ElementID
    if estereotipo <> "" then
        con.Stereotype = estereotipo
    end if
    con.Update()
end sub

' =============================================================
' PUNTO DE ENTRADA AL EJECUTAR EN ENTERPRISE ARCHITECT
' =============================================================
OnDiagramScript
