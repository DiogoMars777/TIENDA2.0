!INC Local Scripts.EAConstants-JScript

// =====================================================================
// Script: Generar Diagramas de Estados y de Tiempo para Procesos Clave
// Proyecto: T-Shirt Boutique ERP & E-Commerce (ECOMMERCE_TIENDA)
// Herramienta: Enterprise Architect 15 / 16 (Versión JavaScript / JScript)
// =====================================================================

function OnDiagramScript() {
    var currentPackage = Repository.GetTreeSelectedPackage();
    if (!currentPackage) {
        Session.Prompt("Por favor selecciona un Paquete en el Project Browser.", promptOK);
        return;
    }

    var pkgComportamiento = obtenerOCrearSubpaquete(currentPackage, "Diagramas_Comportamiento_Procesos");

    // 1. DIAGRAMAS DE ESTADO (STATE MACHINE)
    crearDiagramaEstadoReserva(pkgComportamiento);
    crearDiagramaEstadoVentaDigital(pkgComportamiento);
    crearDiagramaEstadoVentaPOS(pkgComportamiento);
    crearDiagramaEstadoSesion(pkgComportamiento);

    // 2. DIAGRAMAS DE TIEMPO (TIMING DIAGRAMS)
    crearDiagramaTiempoReserva(pkgComportamiento);
    crearDiagramaTiempoCheckout(pkgComportamiento);

    Repository.RefreshModelView(0);
    Session.Prompt("¡Se generaron con éxito los 4 Diagramas de Estados y 2 Diagramas de Tiempo en 'Diagramas_Comportamiento_Procesos'!", promptOK);
}

// 1. ESTADO: RESERVA (CU10 - CU11)
function crearDiagramaEstadoReserva(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Estado - Ciclo de Vida de Reserva (CU10-CU11)", "Statechart");

    var ini = crearNodoEstado(pkg, "Ini_Res", 3);
    var eReg = crearEstado(pkg, "Registrada", "Entrada: registrarPrendas()");
    var eConf = crearEstado(pkg, "Confirmada", "Entrada: apartarStockVirtual()\nDo: contador48Horas()");
    var eAten = crearEstado(pkg, "Atendida en Sucursal", "Entrada: descontarStockFisico()\nSalida: generarComprobante()");
    var eExp = crearEstado(pkg, "Expirada", "Entrada: liberarStockVirtual()\nDo: notificarCancelacionAuto()");
    var eCanc = crearEstado(pkg, "Cancelada", "Entrada: devolverStock()\nSalida: notificarCliente()");
    var fin = crearNodoEstado(pkg, "Fin_Res", 4);

    colocarElemento(diag, ini,   50,  80,   -120, -150);
    colocarElemento(diag, eReg,  130, 280,  -100, -170);
    colocarElemento(diag, eConf, 350, 520,  -100, -190);
    colocarElemento(diag, eAten, 600, 790,  -60,  -150);
    colocarElemento(diag, eExp,  600, 790,  -190, -280);
    colocarElemento(diag, eCanc, 350, 520,  -260, -340);
    colocarElemento(diag, fin,   870, 900,  -140, -170);

    var nota = crearNota(pkg, "REGLA DE NEGOCIO (CU10 / CU11):\n- Vigencia maxima de reserva: 48 horas.\n- Si el cliente asiste con su codigo en sucursal: Atendida.\n- Si transcurren 48h: Expiracion automatica y devolucion de stock.");
    colocarElemento(diag, nota, 130, 480, -370, -460);

    crearTransicion(ini, eReg, "CU10: solicitarReserva()");
    crearTransicion(eReg, eConf, "apartarStock() [stockDisponible]");
    crearTransicion(eReg, eCanc, "[stockInsuficiente] / rechazar()");
    crearTransicion(eConf, eAten, "CU11: presentarCodigo() / entregarPrendas()");
    crearTransicion(eConf, eExp, "after(48 horas) / liberarStock()");
    crearTransicion(eConf, eCanc, "CU10: cancelarReserva() / liberarStock()");
    crearTransicion(eAten, fin, "completado");
    crearTransicion(eExp, fin, "expirado");
    crearTransicion(eCanc, fin, "finalizado");

    Repository.SaveDiagram(diag.DiagramID);
}

// 2. ESTADO: VENTA DIGITAL (CU09 - CU15)
function crearDiagramaEstadoVentaDigital(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Estado - Ciclo de Venta Digital (CU09-CU15)", "Statechart");

    var ini = crearNodoEstado(pkg, "Ini_VD", 3);
    var eCar = crearEstado(pkg, "Carrito Activo", "Do: actualizarSubtotales()");
    var eChk = crearEstado(pkg, "Checkout Iniciado", "Entrada: retenerStock(15 min)");
    var ePend = crearEstado(pkg, "Pago Pendiente", "Do: esperarWebhookPasarela()");
    var ePag = crearEstado(pkg, "Pagado", "Entrada: emitirReciboDigital()");
    var ePrep = crearEstado(pkg, "En Preparacion", "Do: empaquetarPrendas()");
    var eRet = crearEstado(pkg, "Listo para Recojo", "Entrada: enviarNotifRetiro()");
    var eEnv = crearEstado(pkg, "En Envio Delivery", "Do: trackingTransporte()");
    var eEnt = crearEstado(pkg, "Entregado", "Entrada: registrarFirmaRecepcion()");
    var eCanc = crearEstado(pkg, "Cancelado / Fallido", "Entrada: liberarStock()");
    var fin = crearNodoEstado(pkg, "Fin_VD", 4);

    colocarElemento(diag, ini,   40,   70,   -110, -140);
    colocarElemento(diag, eCar,  110,  240,  -90,  -160);
    colocarElemento(diag, eChk,  280,  420,  -90,  -160);
    colocarElemento(diag, ePend, 460,  600,  -90,  -160);
    colocarElemento(diag, ePag,  640,  780,  -90,  -160);
    colocarElemento(diag, ePrep, 820,  960,  -90,  -160);
    colocarElemento(diag, eRet,  1010, 1160, -40,  -110);
    colocarElemento(diag, eEnv,  1010, 1160, -150, -220);
    colocarElemento(diag, eEnt,  1210, 1340, -90,  -160);
    colocarElemento(diag, fin,   1390, 1420, -110, -140);
    colocarElemento(diag, eCanc, 370,  510,  -230, -300);

    crearTransicion(ini, eCar, "CU09: agregarItem()");
    crearTransicion(eCar, eChk, "CU15: iniciarCheckout()");
    crearTransicion(eChk, ePend, "seleccionarMetodoPago()");
    crearTransicion(ePend, ePag, "webhookPagoExitoso()");
    crearTransicion(ePend, eCanc, "timeout(15 min) o rechazoPago()");
    crearTransicion(eChk, eCanc, "abandonarCheckout()");
    crearTransicion(ePag, ePrep, "asignarAlmacen()");
    crearTransicion(ePrep, eRet, "[tipoEntrega == Sucursal]");
    crearTransicion(ePrep, eEnv, "[tipoEntrega == Delivery]");
    crearTransicion(eRet, eEnt, "clienteRetiraEnSucursal()");
    crearTransicion(eEnv, eEnt, "confirmarRecepcionCliente()");
    crearTransicion(eEnt, fin, "ordenFinalizada");
    crearTransicion(eCanc, fin, "ordenCancelada");

    Repository.SaveDiagram(diag.DiagramID);
}

// 3. ESTADO: VENTA POS (CU14)
function crearDiagramaEstadoVentaPOS(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Estado - Venta Presencial POS (CU14)", "Statechart");

    var ini = crearNodoEstado(pkg, "Ini_POS", 3);
    var eAbt = crearEstado(pkg, "Caja Abierta", "Entrada: verificarTurnoCajero()");
    var eReg = crearEstado(pkg, "Registrando Prendas", "Do: escanearBarras()\nDo: aplicarDescuento()");
    var eCob = crearEstado(pkg, "Esperando Cobro", "Do: seleccionarEfectivoQR()");
    var ePag = crearEstado(pkg, "Cobrada", "Entrada: calcularCambio()");
    var eFact = crearEstado(pkg, "Facturada y Finalizada", "Entrada: emitirTicket()\nEntrada: rebajarKardex()");
    var eCanc = crearEstado(pkg, "Venta Anulada", "Entrada: restaurarItems()");
    var fin = crearNodoEstado(pkg, "Fin_POS", 4);

    colocarElemento(diag, ini,   50,   80,   -110, -140);
    colocarElemento(diag, eAbt,  120,  240,  -90,  -160);
    colocarElemento(diag, eReg,  290,  440,  -90,  -170);
    colocarElemento(diag, eCob,  490,  630,  -90,  -160);
    colocarElemento(diag, ePag,  680,  800,  -90,  -160);
    colocarElemento(diag, eFact, 850,  1000, -90,  -170);
    colocarElemento(diag, fin,   1050, 1080, -110, -140);
    colocarElemento(diag, eCanc, 390,  530,  -230, -300);

    crearTransicion(ini, eAbt, "abrirSesionCaja()");
    crearTransicion(eAbt, eReg, "iniciarNuevaVenta()");
    crearTransicion(eReg, eReg, "escanearItem() / sumarItem()");
    crearTransicion(eReg, eCob, "finalizarLecturaPrendas()");
    crearTransicion(eCob, ePag, "pagoConfirmado()");
    crearTransicion(eCob, eCanc, "cancelarOperacion()");
    crearTransicion(eReg, eCanc, "descartarCarrito()");
    crearTransicion(ePag, eFact, "imprimirTicket() / actualizarKardex()");
    crearTransicion(eFact, fin, "ventaExitosa");
    crearTransicion(eCanc, fin, "ventaDescartada");

    Repository.SaveDiagram(diag.DiagramID);
}

// 4. ESTADO: SESION JWT (CU01)
function crearDiagramaEstadoSesion(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Estado - Sesion y Token JWT (CU01)", "Statechart");

    var ini = crearNodoEstado(pkg, "Ini_Ses", 3);
    var eSin = crearEstado(pkg, "Sin Autenticar", "Entrada: limpiarStorage()");
    var eAut = crearEstado(pkg, "Autenticado (Token Valido)", "Entrada: almacenarJWT()\nDo: contadorExpiracion(2h)");
    var eBloq = crearEstado(pkg, "Temporalmente Bloqueado", "Entrada: contadorBloqueo(15m)");
    var eRen = crearEstado(pkg, "Token Renovado", "Entrada: nuevoRefreshToken()");
    var fin = crearNodoEstado(pkg, "Fin_Ses", 4);

    colocarElemento(diag, ini,   50,  80,   -110, -140);
    colocarElemento(diag, eSin,  130, 270,  -90,  -160);
    colocarElemento(diag, eAut,  340, 520,  -90,  -180);
    colocarElemento(diag, eRen,  340, 520,  -240, -310);
    colocarElemento(diag, eBloq, 130, 270,  -240, -310);
    colocarElemento(diag, fin,   600, 630,  -110, -140);

    crearTransicion(ini, eSin, "abrirAplicacion()");
    crearTransicion(eSin, eAut, "loginExitoso(credenciales) / generarJWT()");
    crearTransicion(eSin, eBloq, "[intentosFallidos >= 5] / activarBloqueo()");
    crearTransicion(eBloq, eSin, "timeout(15 min) / desbloquear()");
    crearTransicion(eAut, eRen, "refrescarToken() [vidaToken < 30m]");
    crearTransicion(eRen, eAut, "tokenActualizado");
    crearTransicion(eAut, eSin, "logout() o timeout(2h sin actividad)");
    crearTransicion(eAut, fin, "cerrarApp");

    Repository.SaveDiagram(diag.DiagramID);
}

// 5. TIEMPO: RESERVA (CU10 - CU11)
function crearDiagramaTiempoReserva(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Tiempo - Control de Vigencia de Reserva 48h (CU10-CU11)", "Timing");

    var llReserva = crearTimeLine(pkg, "Reserva_Prenda", "Estados: Inactiva | Registrada | Confirmada | Expirada | Atendida");
    var llStock = crearTimeLine(pkg, "Stock_Sucursal", "Estados: Disponible | RetenidoVirtual | DescontadoFisico");
    var llTimer = crearTimeLine(pkg, "CronJob_Expiracion", "Estados: Idle | Monitoreando(t < 48h) | DisparoTimeout(t = 48h)");

    colocarElemento(diag, llReserva, 50, 820, -40,  -130);
    colocarElemento(diag, llStock,   50, 820, -160, -250);
    colocarElemento(diag, llTimer,   50, 820, -280, -370);

    var notaRestriccion = crearNota(pkg, "RESTRICCIONES TEMPORALES UML:\n- {t_apartado <= 48 horas}\n- {duracion_atencion <= 48 horas}\n- A t = 0s: Cliente reserva prenda (Stock pasa a Retenido).\n- A t = 48h: Si el cliente NO se presento, se dispara Timeout.\n- Efecto Timeout: Reserva -> Expirada, Stock -> Disponible.");
    colocarElemento(diag, notaRestriccion, 850, 1180, -40, -260);

    Repository.SaveDiagram(diag.DiagramID);
}

// 6. TIEMPO: CHECKOUT 15 MIN (CU15)
function crearDiagramaTiempoCheckout(pkg) {
    var diag = crearDiagramaLimpio(pkg, "Tiempo - Timeout de Pasarela de Pago 15min (CU15)", "Timing");

    var llOrden = crearTimeLine(pkg, "Orden_Digital", "Estados: EnEdicion | EnCheckout | Pagada | CanceladaTimeout");
    var llStockTemp = crearTimeLine(pkg, "Stock_BloqueoTemporal", "Estados: Libre | RetenidoTemporal | ConsolidadoVenta");
    var llPasarela = crearTimeLine(pkg, "Pasarela_Webhook", "Estados: Inactivo | EsperandoConfirmacion | Confirmado | Expirado");

    colocarElemento(diag, llOrden,     50, 820, -40,  -130);
    colocarElemento(diag, llStockTemp, 50, 820, -160, -250);
    colocarElemento(diag, llPasarela,  50, 820, -280, -370);

    var notaCheckout = crearNota(pkg, "RESTRICCION TEMPORAL DE CHECKOUT:\n- {t_pago < 15 minutos}\n- A t = 0 min: Inicia checkout, se genera token de pago y se retiene stock.\n- Si t < 15 min y Webhook responde: Estado pasa a Pagada.\n- Si t >= 15 min sin respuesta: Se anula el checkout y se desbloquea el stock.");
    colocarElemento(diag, notaCheckout, 850, 1180, -40, -260);

    Repository.SaveDiagram(diag.DiagramID);
}

// AUXILIARES
function obtenerOCrearSubpaquete(parentPkg, nombre) {
    for (var i = 0; i < parentPkg.Packages.Count; i++) {
        var p = parentPkg.Packages.GetAt(i);
        if (p.Name == nombre) return p;
    }
    var newPkg = parentPkg.Packages.AddNew(nombre, "");
    newPkg.Update();
    parentPkg.Packages.Refresh();
    return newPkg;
}

function crearDiagramaLimpio(package, name, tipo) {
    for (var i = package.Diagrams.Count - 1; i >= 0; i--) {
        var d = package.Diagrams.GetAt(i);
        if (d.Name == name) {
            for (var j = d.DiagramObjects.Count - 1; j >= 0; j--) d.DiagramObjects.Delete(j);
            for (var k = d.DiagramLinks.Count - 1; k >= 0; k--) d.DiagramLinks.Delete(k);
            d.DiagramObjects.Refresh();
            d.DiagramLinks.Refresh();
            d.Update();
            return d;
        }
    }
    var diag = package.Diagrams.AddNew(name, tipo);
    diag.Update();
    package.Diagrams.Refresh();
    return diag;
}

function crearEstado(package, nombre, notas) {
    for (var i = 0; i < package.Elements.Count; i++) {
        var el = package.Elements.GetAt(i);
        if (el.Name == nombre && el.Type == "State") {
            el.Notes = notas;
            el.Update();
            return el;
        }
    }
    var newEl = package.Elements.AddNew(nombre, "State");
    newEl.Notes = notas;
    newEl.Update();
    package.Elements.Refresh();
    return newEl;
}

function crearNodoEstado(package, nombre, subtipo) {
    for (var i = 0; i < package.Elements.Count; i++) {
        var el = package.Elements.GetAt(i);
        if (el.Name == nombre && el.Type == "StateNode") return el;
    }
    var newEl = package.Elements.AddNew(nombre, "StateNode");
    newEl.Subtype = subtipo;
    newEl.Update();
    package.Elements.Refresh();
    return newEl;
}

function crearTimeLine(package, nombre, notas) {
    var deleteIndex = -1;
    for (var i = 0; i < package.Elements.Count; i++) {
        var el = package.Elements.GetAt(i);
        if (el.Name == nombre) {
            if (el.Type == "TimeLine") {
                el.Notes = notas;
                el.Update();
                return el;
            } else {
                deleteIndex = i;
                break;
            }
        }
    }
    if (deleteIndex >= 0) {
        package.Elements.Delete(deleteIndex);
        package.Elements.Refresh();
    }
    var newEl = null;
    try {
        newEl = package.Elements.AddNew(nombre, "TimeLine");
        newEl.Subtype = 0; // 0 = State Lifeline
    } catch(e) {
        newEl = package.Elements.AddNew(nombre, "Sequence");
    }
    if (newEl) {
        newEl.Notes = notas;
        newEl.Update();
        package.Elements.Refresh();
    }
    return newEl;
}

function crearNota(package, contenido) {
    var el = package.Elements.AddNew("", "Note");
    el.Notes = contenido;
    el.Update();
    package.Elements.Refresh();
    return el;
}

function colocarElemento(diagram, elemento, left, right, top, bottom) {
    var diagObj = diagram.DiagramObjects.AddNew("l=" + left + ";r=" + right + ";t=" + top + ";b=" + bottom + ";", "");
    diagObj.ElementID = elemento.ElementID;
    diagObj.Update();
}

function crearTransicion(origen, destino, nombreEvento) {
    for (var i = 0; i < origen.Connectors.Count; i++) {
        var con = origen.Connectors.GetAt(i);
        if (con.SupplierID == destino.ElementID && (con.Type == "StateFlow" || con.Type == "Transition")) {
            if (con.Name == nombreEvento) return;
        }
    }
    var newCon = origen.Connectors.AddNew(nombreEvento, "StateFlow");
    newCon.SupplierID = destino.ElementID;
    newCon.Update();
    origen.Connectors.Refresh();
}

OnDiagramScript();
