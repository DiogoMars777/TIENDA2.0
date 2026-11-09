option explicit

!INC Local Scripts.EAConstants-VBScript

' =====================================================================
' Script: Generar Diagramas de Tiempo (UML Timing Diagram)
' Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
' Herramienta: Enterprise Architect 15 / 16
'
' Modelado con 4 Líneas de Vida (Lifelines), exactamente como el estándar UML 2.0:
'   1. :Backend_CompraDigitalController (FastAPI)
'   2. :Inventario_Kardex (InventarioModel / Stock)
'   3. :Frontend_UI_Checkout (Angular Boutique)
'   4. :Cliente_WebUser (Usuario Comprador)
'
' Incluye:
'   - Pistas de tiempo paralelas (State Lifelines)
'   - Mensajes / Estímulos sincronizados (flechas de interacción)
'   - Restricciones de Duración ({50..200 ms}, {0..15 min})
'   - Escala temporal y guía de estados
' =====================================================================

sub OnDiagramScript()
    dim currentPackage
    set currentPackage = Repository.GetTreeSelectedPackage()
    
    if currentPackage is nothing then
        Session.Prompt "Por favor selecciona un Paquete en el Project Browser antes de ejecutar.", promptOK
        exit sub
    end if

    ' 1. Diagrama de Tiempo: Proceso de Compra Digital y Pasarela de Pago (CU15)
    crearDiagramaTiempoCompraDigital currentPackage

    ' 2. Diagrama de Tiempo: Proceso de Reserva de Prendas en Sucursal (CU10 - CU11)
    crearDiagramaTiempoReserva currentPackage

    Repository.RefreshModelView(0)
    Session.Prompt "¡Se generaron con éxito los 2 Diagramas de Tiempo adaptados a la arquitectura de tu proyecto!", promptOK
end sub

' =====================================================================
' 1. TIEMPO: PROCESO DE COMPRA DIGITAL Y PASARELA DE PAGO (CU15)
' =====================================================================
sub crearDiagramaTiempoCompraDigital(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "sd Compra Digital y Pasarela (CU15)", "Timing")

    ' 4 Líneas de vida según la arquitectura real del proyecto
    dim llBackend, llInventario, llFrontend, llCliente
    set llBackend    = crearTimeLine(pkg, ":Backend_CompraDigitalController", "Estados: Idle | ValidandoStock | EsperandoWebhook | ConfirmandoVenta")
    set llInventario = crearTimeLine(pkg, ":Inventario_Kardex",               "Estados: StockDisponible | RetenidoTemporal | DescontadoKardex")
    set llFrontend   = crearTimeLine(pkg, ":Frontend_UI_Checkout",             "Estados: Idle | EnviandoOrden | MostrandoPagoQR | MostrandoRecibo")
    set llCliente    = crearTimeLine(pkg, ":Cliente_WebUser",                  "Estados: Idle | EnCheckout | PagandoBancoQR | ViendoRecibo")

    ' Posicionamiento horizontal apilado (de arriba hacia abajo como en el estandar UML)
    colocarElemento diag, llBackend,    "50", "850", "-30",  "-110"
    colocarElemento diag, llInventario, "50", "850", "-130", "-210"
    colocarElemento diag, llFrontend,   "50", "850", "-230", "-310"
    colocarElemento diag, llCliente,    "50", "850", "-330", "-410"

    ' Mensajes / Estímulos entre las pistas de tiempo
    crearMensajeEstimulo llCliente,    llFrontend,   "1. clicIniciarCheckout()"
    crearMensajeEstimulo llFrontend,   llBackend,    "2. POST /api/v1/compras/procesar"
    crearMensajeEstimulo llBackend,    llInventario, "3. retenerStockTemporal()"
    crearMensajeEstimulo llBackend,    llFrontend,   "4. sesionPagoCreada(QR/Stripe)"
    crearMensajeEstimulo llFrontend,   llCliente,    "5. escanearQR_o_Pagar()"
    crearMensajeEstimulo llBackend,    llInventario, "6. webhookExito() / rebajarKardex()"
    crearMensajeEstimulo llBackend,    llFrontend,   "7. ventaConfirmada(VentaModel)"
    crearMensajeEstimulo llFrontend,   llCliente,    "8. renderizarComprobanteDigital()"

    ' Restricciones de duración formales UML
    dim notaRestricciones
    set notaRestricciones = crearNota(pkg, "RESTRICCIONES TEMPORALES UML (CU15):" & vbCrLf & _
                                           "--------------------------------------------------" & vbCrLf & _
                                           "• {50..200 ms}: Latencia HTTP Frontend -> Backend" & vbCrLf & _
                                           "• {100..400 ms}: Validacion y Bloqueo atomico en BD" & vbCrLf & _
                                           "• {0..15 min}: Ventana maxima para pago QR / Stripe" & vbCrLf & _
                                           "• {< 3 s}: Webhook de confirmacion de pasarela" & vbCrLf & _
                                           "--------------------------------------------------" & vbCrLf & _
                                           "Regla de negocio: Si pasan 15 min sin respuesta del" & vbCrLf & _
                                           "Webhook, el Backend libera el stock retenido y anula la orden.")
    colocarElemento diag, notaRestricciones, "880", "1260", "-30", "-270"

    Repository.SaveDiagram diag.DiagramID
    Repository.ReloadDiagram diag.DiagramID
    Repository.OpenDiagram diag.DiagramID
end sub

' =====================================================================
' 2. TIEMPO: PROCESO DE RESERVA DE PRENDAS EN SUCURSAL (CU10 - CU11)
' =====================================================================
sub crearDiagramaTiempoReserva(pkg)
    dim diag
    set diag = crearDiagramaLimpio(pkg, "sd Reserva de Prendas (CU10-CU11)", "Timing")

    dim llCronJob, llBackend, llStock, llCliente
    set llCronJob = crearTimeLine(pkg, ":CronJob_Expirador",           "Estados: Idle | Monitoreando(t < 48h) | DisparoTimeout(t = 48h)")
    set llBackend = crearTimeLine(pkg, ":Backend_ReservaController",   "Estados: Idle | GenerandoCodigo | AtendiendoEnSucursal | Cancelando")
    set llStock   = crearTimeLine(pkg, ":InventarioSucursal_Model",    "Estados: StockDisponible | StockReservado | DescontadoFisico")
    set llCliente = crearTimeLine(pkg, ":Cliente_Comprador",           "Estados: CarritoActivo | EsperandoRetiro | RetirandoEnSucursal")

    colocarElemento diag, llCronJob, "50", "850", "-30",  "-110"
    colocarElemento diag, llBackend, "50", "850", "-130", "-210"
    colocarElemento diag, llStock,   "50", "850", "-230", "-310"
    colocarElemento diag, llCliente, "50", "850", "-330", "-410"

    crearMensajeEstimulo llCliente, llBackend, "1. POST /api/v1/reservas/desde-carrito"
    crearMensajeEstimulo llBackend, llStock,   "2. incrementar stockreservado"
    crearMensajeEstimulo llBackend, llCronJob, "3. iniciarTemporizador(48h)"
    crearMensajeEstimulo llCliente, llBackend, "4. CU11: presentarCodigo(RES-XXXX)"
    crearMensajeEstimulo llBackend, llStock,   "5. rebajar stockfisico y stockreservado"

    dim notaReserva
    set notaReserva = crearNota(pkg, "RESTRICCIONES TEMPORALES UML (CU10 / CU11):" & vbCrLf & _
                                     "--------------------------------------------------" & vbCrLf & _
                                     "• {0..48 horas}: Vigencia maxima para retiro en sucursal" & vbCrLf & _
                                     "• A t = 0h: Se reserva stock e inicia cuenta regresiva." & vbCrLf & _
                                     "• Si t <= 48h y cliente asiste: Se atiende y descuenta stock." & vbCrLf & _
                                     "• Si t > 48h sin atencion: CronJob ejecuta liberacion de stock.")
    colocarElemento diag, notaReserva, "880", "1260", "-30", "-250"

    Repository.SaveDiagram diag.DiagramID
    Repository.ReloadDiagram diag.DiagramID
    Repository.OpenDiagram diag.DiagramID
end sub

' =====================================================================
' FUNCIONES AUXILIARES AUTOMATIZADAS
' =====================================================================

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
        el.Subtype = 0 ' 0 = State Lifeline horizontal
    end if
    on error goto 0
    
    if not el is nothing then
        el.Notes = notas
        el.Update()
        package.Elements.Refresh()
    end if
    set crearTimeLine = el
end function

sub crearMensajeEstimulo(origen, destino, nombreMensaje)
    dim con
    on error resume next
    set con = origen.Connectors.AddNew(nombreMensaje, "TimingMessage")
    if err.number <> 0 or con is nothing then
        err.clear
        set con = origen.Connectors.AddNew(nombreMensaje, "Message")
    end if
    if not con is nothing then
        con.SupplierID = destino.ElementID
        con.Update()
        origen.Connectors.Refresh()
    end if
    on error goto 0
end sub

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

' =====================================================================
' PUNTO DE ENTRADA
' =====================================================================
OnDiagramScript
