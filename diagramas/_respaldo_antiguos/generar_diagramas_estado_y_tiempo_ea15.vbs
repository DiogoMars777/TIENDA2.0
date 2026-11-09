option explicit

!INC Local Scripts.EAConstants-VBScript

' =====================================================================
' Script: Generar Diagramas de Estados y de Tiempo para Procesos Clave
' Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
' Herramienta: Enterprise Architect 15 / 16
' Casos de Uso: 
'   - Proceso 1: Ciclo de Vida de Reserva (CU10 y CU11) -> Estado y Tiempo (48h)
'   - Proceso 2: Compra Digital y Checkout (CU09 y CU15) -> Estado y Tiempo (15 min)
'   - Proceso 3: Venta Presencial POS (CU14) -> Estado
'   - Proceso 4: Sesión y Autenticación JWT (CU01) -> Estado
' =====================================================================

sub OnDiagramScript()
    dim currentPackage
    set currentPackage = Repository.GetTreeSelectedPackage()
    
    if currentPackage is nothing then
        Session.Prompt "Por favor, selecciona un Paquete en el Project Browser antes de ejecutar.", promptOK
        exit sub
    end if

    ' Crear subpaquete para organizar los diagramas de comportamiento
    dim pkgComportamiento
    set pkgComportamiento = obtenerOCrearSubpaquete(currentPackage, "Diagramas_Comportamiento_Procesos")

    ' --- 1. DIAGRAMAS DE ESTADO (STATE MACHINE) ---
    crearDiagramaEstadoReserva pkgComportamiento
    crearDiagramaEstadoVentaDigital pkgComportamiento
    crearDiagramaEstadoVentaPOS pkgComportamiento
    crearDiagramaEstadoSesion pkgComportamiento

    ' --- 2. DIAGRAMAS DE TIEMPO (TIMING DIAGRAMS) ---
    crearDiagramaTiempoReserva pkgComportamiento
    crearDiagramaTiempoCheckout pkgComportamiento

    Repository.RefreshModelView(0)
    Session.Prompt "¡Se generaron exitosamente los 4 Diagramas de Estados y 2 Diagramas de Tiempo en el paquete 'Diagramas_Comportamiento_Procesos'!", promptOK
end sub

' =====================================================================
' 1. ESTADO: CICLO DE VIDA DE LA RESERVA (CU10 - CU11)
' =====================================================================
sub crearDiagramaEstadoReserva(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Estado - Ciclo de Vida de Reserva (CU10-CU11)", "Statechart")

    ' Crear nodos y estados
    dim ini, eReg, eConf, eAten, eExp, eCanc, fin
    set ini = crearNodoEstado(pkg, "Ini_Res", 3)
    set eReg = crearEstado(pkg, "Registrada", "Entrada: registrarPrendas()")
    set eConf = crearEstado(pkg, "Confirmada", "Entrada: apartarStockVirtual()" & vbCrLf & "Do: contador48Horas()")
    set eAten = crearEstado(pkg, "Atendida en Sucursal", "Entrada: descontarStockFisico()" & vbCrLf & "Salida: generarComprobante()")
    set eExp = crearEstado(pkg, "Expirada", "Entrada: liberarStockVirtual()" & vbCrLf & "Do: notificarCancelacionAuto()")
    set eCanc = crearEstado(pkg, "Cancelada", "Entrada: devolverStock()" & vbCrLf & "Salida: notificarCliente()")
    set fin = crearNodoEstado(pkg, "Fin_Res", 4)

    ' Posicionamiento visual en el diagrama
    colocarElemento diag, ini,   "50",  "80",   "-120", "-150"
    colocarElemento diag, eReg,  "130", "280",  "-100", "-170"
    colocarElemento diag, eConf, "350", "520",  "-100", "-190"
    colocarElemento diag, eAten, "600", "790",  "-60",  "-150"
    colocarElemento diag, eExp,  "600", "790",  "-190", "-280"
    colocarElemento diag, eCanc, "350", "520",  "-260", "-340"
    colocarElemento diag, fin,   "870", "900",  "-140", "-170"

    ' Nota explicativa de negocio
    dim nota
    set nota = crearNota(pkg, "REGLA DE NEGOCIO (CU10 / CU11):" & vbCrLf & _
                              "- Las reservas tienen vigencia maxima de 48 horas." & vbCrLf & _
                              "- Si el cliente se presenta con su codigo en sucursal, se marca Atendida." & vbCrLf & _
                              "- Si pasa el tiempo, el sistema libera automaticamente las prendas.")
    colocarElemento diag, nota, "130", "480", "-370", "-460"

    ' Transiciones
    crearTransicion ini, eReg, "CU10: solicitarReserva()"
    crearTransicion eReg, eConf, "apartarStock() [stockDisponible]"
    crearTransicion eReg, eCanc, "[stockInsuficiente] / rechazar()"
    crearTransicion eConf, eAten, "CU11: presentarCodigo() / entregarPrendas()"
    crearTransicion eConf, eExp, "after(48 horas) / liberarStock()"
    crearTransicion eConf, eCanc, "CU10: cancelarReserva() / liberarStock()"
    crearTransicion eAten, fin, "completado"
    crearTransicion eExp, fin, "expirado"
    crearTransicion eCanc, fin, "finalizado"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' 2. ESTADO: CICLO DE VIDA DE VENTA DIGITAL (CU09 - CU15)
' =====================================================================
sub crearDiagramaEstadoVentaVentaDigital(pkg)
end sub

sub crearDiagramaEstadoVentaDigital(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Estado - Ciclo de Venta Digital (CU09-CU15)", "Statechart")

    dim ini, eCar, eChk, ePend, ePag, ePrep, eRet, eEnv, eEnt, eCanc, fin
    set ini = crearNodoEstado(pkg, "Ini_VD", 3)
    set eCar = crearEstado(pkg, "Carrito Activo", "Do: actualizarSubtotales()")
    set eChk = crearEstado(pkg, "Checkout Iniciado", "Entrada: retenerStock(15 min)")
    set ePend = crearEstado(pkg, "Pago Pendiente", "Do: esperarWebhookPasarela()")
    set ePag = crearEstado(pkg, "Pagado", "Entrada: emitirReciboDigital()")
    set ePrep = crearEstado(pkg, "En Preparacion", "Do: empaquetarPrendas()")
    set eRet = crearEstado(pkg, "Listo para Recojo", "Entrada: enviarNotifRetiro()")
    set eEnv = crearEstado(pkg, "En Envio Delivery", "Do: trackingTransporte()")
    set eEnt = crearEstado(pkg, "Entregado", "Entrada: registrarFirmaRecepcion()")
    set eCanc = crearEstado(pkg, "Cancelado / Fallido", "Entrada: liberarStock()")
    set fin = crearNodoEstado(pkg, "Fin_VD", 4)

    ' Posicionamiento horizontal fluido
    colocarElemento diag, ini,   "40",  "70",   "-110", "-140"
    colocarElemento diag, eCar,  "110", "240",  "-90",  "-160"
    colocarElemento diag, eChk,  "280", "420",  "-90",  "-160"
    colocarElemento diag, ePend, "460", "600",  "-90",  "-160"
    colocarElemento diag, ePag,  "640", "780",  "-90",  "-160"
    colocarElemento diag, ePrep, "820", "960",  "-90",  "-160"

    colocarElemento diag, eRet,  "1010", "1160", "-40",  "-110"
    colocarElemento diag, eEnv,  "1010", "1160", "-150", "-220"
    colocarElemento diag, eEnt,  "1210", "1340", "-90",  "-160"
    colocarElemento diag, fin,   "1390", "1420", "-110", "-140"

    colocarElemento diag, eCanc, "370", "510",  "-230", "-300"

    ' Transiciones
    crearTransicion ini, eCar, "CU09: agregarItem()"
    crearTransicion eCar, eChk, "CU15: iniciarCheckout()"
    crearTransicion eChk, ePend, "seleccionarMetodoPago()"
    crearTransicion ePend, ePag, "webhookPagoExitoso()"
    crearTransicion ePend, eCanc, "timeout(15 min) o rechazoPago()"
    crearTransicion eChk, eCanc, "abandonarCheckout()"
    crearTransicion ePag, ePrep, "asignarAlmacen()"
    crearTransicion ePrep, eRet, "[tipoEntrega == Sucursal]"
    crearTransicion ePrep, eEnv, "[tipoEntrega == Delivery]"
    crearTransicion eRet, eEnt, "clienteRetiraEnSucursal()"
    crearTransicion eEnv, eEnt, "confirmarRecepcionCliente()"
    crearTransicion eEnt, fin, "ordenFinalizada"
    crearTransicion eCanc, fin, "ordenCancelada"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' 3. ESTADO: VENTA PRESENCIAL POS (CU14)
' =====================================================================
sub crearDiagramaEstadoVentaPOS(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Estado - Venta Presencial POS (CU14)", "Statechart")

    dim ini, eAbt, eReg, eCob, ePag, eFact, eCanc, fin
    set ini = crearNodoEstado(pkg, "Ini_POS", 3)
    set eAbt = crearEstado(pkg, "Caja Abierta", "Entrada: verificarTurnoCajero()")
    set eReg = crearEstado(pkg, "Registrando Prendas", "Do: escanearBarras()" & vbCrLf & "Do: aplicarDescuento()")
    set eCob = crearEstado(pkg, "Esperando Cobro", "Do: seleccionarEfectivoQR()")
    set ePag = crearEstado(pkg, "Cobrada", "Entrada: calcularCambio()")
    set eFact = crearEstado(pkg, "Facturada y Finalizada", "Entrada: emitirTicket()" & vbCrLf & "Entrada: rebajarKardex()")
    set eCanc = crearEstado(pkg, "Venta Anulada", "Entrada: restaurarItems()")
    set fin = crearNodoEstado(pkg, "Fin_POS", 4)

    colocarElemento diag, ini,   "50",  "80",   "-110", "-140"
    colocarElemento diag, eAbt,  "120", "240",  "-90",  "-160"
    colocarElemento diag, eReg,  "290", "440",  "-90",  "-170"
    colocarElemento diag, eCob,  "490", "630",  "-90",  "-160"
    colocarElemento diag, ePag,  "680", "800",  "-90",  "-160"
    colocarElemento diag, eFact, "850", "1000", "-90",  "-170"
    colocarElemento diag, fin,   "1050", "1080", "-110", "-140"

    colocarElemento diag, eCanc, "390", "530",  "-230", "-300"

    crearTransicion ini, eAbt, "abrirSesionCaja()"
    crearTransicion eAbt, eReg, "iniciarNuevaVenta()"
    crearTransicion eReg, eReg, "escanearItem() / sumarItem()"
    crearTransicion eReg, eCob, "finalizarLecturaPrendas()"
    crearTransicion eCob, ePag, "pagoConfirmado()"
    crearTransicion eCob, eCanc, "cancelarOperacion()"
    crearTransicion eReg, eCanc, "descartarCarrito()"
    crearTransicion ePag, eFact, "imprimirTicket() / actualizarKardex()"
    crearTransicion eFact, fin, "ventaExitosa"
    crearTransicion eCanc, fin, "ventaDescartada"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' 4. ESTADO: SESION Y TOKEN JWT (CU01)
' =====================================================================
sub crearDiagramaEstadoSesion(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Estado - Sesion y Token JWT (CU01)", "Statechart")

    dim ini, eSin, eAut, eBloq, eRen, fin
    set ini = crearNodoEstado(pkg, "Ini_Ses", 3)
    set eSin = crearEstado(pkg, "Sin Autenticar", "Entrada: limpiarStorage()")
    set eAut = crearEstado(pkg, "Autenticado (Token Valido)", "Entrada: almacenarJWT()" & vbCrLf & "Do: contadorExpiracion(2h)")
    set eBloq = crearEstado(pkg, "Temporalmente Bloqueado", "Entrada: contadorBloqueo(15m)")
    set eRen = crearEstado(pkg, "Token Renovado", "Entrada: nuevoRefreshToken()")
    set fin = crearNodoEstado(pkg, "Fin_Ses", 4)

    colocarElemento diag, ini,   "50",  "80",   "-110", "-140"
    colocarElemento diag, eSin,  "130", "270",  "-90",  "-160"
    colocarElemento diag, eAut,  "340", "520",  "-90",  "-180"
    colocarElemento diag, eRen,  "340", "520",  "-240", "-310"
    colocarElemento diag, eBloq, "130", "270",  "-240", "-310"
    colocarElemento diag, fin,   "600", "630",  "-110", "-140"

    crearTransicion ini, eSin, "abrirAplicacion()"
    crearTransicion eSin, eAut, "loginExitoso(credenciales) / generarJWT()"
    crearTransicion eSin, eBloq, "[intentosFallidos >= 5] / activarBloqueo()"
    crearTransicion eBloq, eSin, "timeout(15 min) / desbloquear()"
    crearTransicion eAut, eRen, "refrescarToken() [vidaToken < 30m]"
    crearTransicion eRen, eAut, "tokenActualizado"
    crearTransicion eAut, eSin, "logout() o timeout(2h sin actividad)"
    crearTransicion eAut, fin, "cerrarApp"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' 5. TIEMPO: PROCESO TEMPORAL DE RESERVA (CU10 - CU11) (Vigencia 48h)
' =====================================================================
sub crearDiagramaTiempoReserva(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Tiempo - Control de Vigencia de Reserva 48h (CU10-CU11)", "Timing")

    ' En diagramas de tiempo, se crean TimeLine (State Lifelines horizontales)
    dim llReserva, llStock, llTimer
    set llReserva = crearTimeLine(pkg, "Reserva_Prenda", "Estados: Inactiva | Registrada | Confirmada | Expirada | Atendida")
    set llStock = crearTimeLine(pkg, "Stock_Sucursal", "Estados: Disponible | RetenidoVirtual | DescontadoFisico")
    set llTimer = crearTimeLine(pkg, "CronJob_Expiracion", "Estados: Idle | Monitoreando(t < 48h) | DisparoTimeout(t = 48h)")

    ' Posicionamiento horizontal de pistas de tiempo (tracks)
    colocarElemento diag, llReserva, "50", "820", "-40",  "-130"
    colocarElemento diag, llStock,   "50", "820", "-160", "-250"
    colocarElemento diag, llTimer,   "50", "820", "-280", "-370"

    ' Nota de restricción temporal formal UML
    dim notaRestriccion
    set notaRestriccion = crearNota(pkg, "RESTRICCIONES TEMPORALES UML:" & vbCrLf & _
                                         "- {t_apartado <= 48 horas}" & vbCrLf & _
                                         "- {duracion_atencion <= 48 horas}" & vbCrLf & _
                                         "- A t = 0s: Cliente reserva prenda (Stock pasa a Retenido)." & vbCrLf & _
                                         "- A t = 48h: Si el cliente NO se presento, se dispara Timeout." & vbCrLf & _
                                         "- Efecto Timeout: Reserva -> Expirada, Stock -> Disponible.")
    colocarElemento diag, notaRestriccion, "850", "1180", "-40", "-260"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' 6. TIEMPO: TIMEOUT DE PASARELA DE PAGO (CU15) (Ventana 15 min)
' =====================================================================
sub crearDiagramaTiempoCheckout(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "Tiempo - Timeout de Pasarela de Pago 15min (CU15)", "Timing")

    dim llOrden, llStockTemp, llPasarela
    set llOrden = crearTimeLine(pkg, "Orden_Digital", "Estados: EnEdicion | EnCheckout | Pagada | CanceladaTimeout")
    set llStockTemp = crearTimeLine(pkg, "Stock_BloqueoTemporal", "Estados: Libre | RetenidoTemporal | ConsolidadoVenta")
    set llPasarela = crearTimeLine(pkg, "Pasarela_Webhook", "Estados: Inactivo | EsperandoConfirmacion | Confirmado | Expirado")

    colocarElemento diag, llOrden,     "50", "820", "-40",  "-130"
    colocarElemento diag, llStockTemp, "50", "820", "-160", "-250"
    colocarElemento diag, llPasarela,  "50", "820", "-280", "-370"

    dim notaCheckout
    set notaCheckout = crearNota(pkg, "RESTRICCION TEMPORAL DE CHECKOUT:" & vbCrLf & _
                                      "- {t_pago < 15 minutos}" & vbCrLf & _
                                      "- A t = 0 min: Inicia checkout, se genera token de pago y se retiene stock." & vbCrLf & _
                                      "- Si t < 15 min y Webhook responde: Estado pasa a Pagada." & vbCrLf & _
                                      "- Si t >= 15 min sin respuesta: Se anula el checkout y se desbloquea el stock.")
    colocarElemento diag, notaCheckout, "850", "1180", "-40", "-260"

    Repository.SaveDiagram diag.DiagramID
end sub

' =====================================================================
' FUNCIONES AUXILIARES AUTOMATIZADAS
' =====================================================================

function obtenerOCrearSubpaquete(parentPkg, nombre)
    dim p
    for each p in parentPkg.Packages
        if p.Name = nombre then
            set obtenerOCrearSubpaquete = p
            exit function
        end if
    next
    set p = parentPkg.Packages.AddNew(nombre, "")
    p.Update()
    parentPkg.Packages.Refresh()
    set obtenerOCrearSubpaquete = p
end function

function crearDiagramaLimpio(package, name, tipo)
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
    set diag = package.Diagrams.AddNew(name, tipo)
    diag.Update()
    package.Diagrams.Refresh()
    set crearDiagramaLimpio = diag
end function

function crearEstado(package, nombre, notas)
    dim el
    for each el in package.Elements
        if el.Name = nombre and el.Type = "State" then
            el.Notes = notas
            el.Update()
            set crearEstado = el
            exit function
        end if
    next
    set el = package.Elements.AddNew(nombre, "State")
    el.Notes = notas
    el.Update()
    package.Elements.Refresh()
    set crearEstado = el
end function

function crearNodoEstado(package, nombre, subtipo)
    ' Subtipo 3 = Initial, 4 = Final State
    dim el
    for each el in package.Elements
        if el.Name = nombre and el.Type = "StateNode" then
            set crearNodoEstado = el
            exit function
        end if
    next
    set el = package.Elements.AddNew(nombre, "StateNode")
    el.Subtype = subtipo
    el.Update()
    package.Elements.Refresh()
    set crearNodoEstado = el
end function

function crearTimeLine(package, nombre, notas)
    dim el, i, deleteIndex
    deleteIndex = -1
    for i = 0 to package.Elements.Count - 1
        set el = package.Elements.GetAt(i)
        if el.Name = nombre then
            if el.Type = "TimeLine" then
                el.Notes = notas
                el.Update()
                set crearTimeLine = el
                exit function
            else
                deleteIndex = i
                exit for
            end if
        end if
    next
    
    if deleteIndex >= 0 then
        package.Elements.Delete deleteIndex
        package.Elements.Refresh()
    end if
    
    on error resume next
    set el = package.Elements.AddNew(nombre, "TimeLine")
    if err.number <> 0 or el is nothing then
        err.clear
        set el = package.Elements.AddNew(nombre, "Sequence")
    else
        el.Subtype = 0 ' 0 = State Lifeline
    end if
    on error goto 0
    
    if not el is nothing then
        el.Notes = notas
        el.Update()
        package.Elements.Refresh()
    end if
    set crearTimeLine = el
end function

function crearNota(package, contenido)
    dim el
    set el = package.Elements.AddNew("", "Note")
    el.Notes = contenido
    el.Update()
    package.Elements.Refresh()
    set crearNota = el
end function

sub colocarElemento(diagram, elemento, left, right, top, bottom)
    dim diagObj
    set diagObj = diagram.DiagramObjects.AddNew("l=" & left & ";r=" & right & ";t=" & top & ";b=" & bottom & ";", "")
    diagObj.ElementID = elemento.ElementID
    diagObj.Update()
end sub

sub crearTransicion(origen, destino, nombreEvento)
    dim con
    for each con in origen.Connectors
        if con.SupplierID = destino.ElementID and (con.Type = "StateFlow" or con.Type = "Transition") then
            if con.Name = nombreEvento then exit sub
        end if
    next
    set con = origen.Connectors.AddNew(nombreEvento, "StateFlow")
    con.SupplierID = destino.ElementID
    con.Update()
    origen.Connectors.Refresh()
end sub

' =====================================================================
' PUNTO DE ENTRADA
' =====================================================================
OnDiagramScript
