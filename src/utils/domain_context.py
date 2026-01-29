
# Contexto de Dominio del Ecosistema Solkos
# Este archivo contiene la información base para que el LLM entienda
# qué es cada proyecto, quién es quién, y cómo conectar los temas.

TEAM_MEMBERS = """
- Emilio Hernandez: Desarrollador Mobile Fullstack (Apps Android: Coolector, Negocon, Cooltech).
- Abraham Agusndis: Desarrollador Backend (Infraestructura, APIs, Solkos Cloud).
- Dani Neri: Data Analyst.
- Carlos Orozco (Charly): AI Engineer (Agentes, Solkos Intelligence).
- Mayra Barron: Lead Frontend (Consola Solkos).
- Cesar: Dev Jr (Frontend).
- Emma Rico: Diseñadora UI.
- Alberto Álvarez: Product Manager / Designer.
- Faustino Neri: Senior Dev (Fundador técnico, Arquitecto).
"""

PROJECTS_CONTEXT = """
---
Hoja de Producto: Solkos Consola

⸻

¿Qué es?
Una plataforma web que centraliza y analiza toda la telemetría de los enfriadores comerciales de Imbera. Recibe los datos que Coolector (la app móvil instalada en preventas) captura vía Bluetooth en campo.

⸻

¿Para quién?
	•	Clientes comerciales grandes (Coca-Cola, Heineken, Lala, Bonafont, etc.) que tienen refrigeradores consignados en puntos de venta.
	•	Gerentes de operaciones y equipos de mantenimiento que necesitan visibilidad y control de su parque de enfriadores.

⸻

¿Qué hace?
	1.	Visión general (“Cooler Insights”)
	•	Mapa de zonas y rutas activas.
	•	KPIs clave:
	•	Cobertura: % de enfriadores leídos (última semana).
	•	Coincidencia geográfica: % de equipos presentes en la ubicación esperada (≤ 50 m).
	•	Frecuencia de visitas: % de enfriadores leídos en los últimos 7 días.
	•	Visitas exitosas: % de conexiones completas que trajeron telemetría válida.
	•	Rendimiento de la flota: % de enfriadores analizados, funcionando, en falla y atendidos.
	•	Control de activos (“Asset Management”):
	•	No risk (ubicación ok).
	•	No risk – No sale (sin ventas).
	•	Visit store – No sale (sin ventas, requiere visita).
	•	Visit store – Data collection (conexión débil, necesita más tiempo de lectura).
	•	No coincidence (cambio de ubicación).
	•	In warehouse (en almacén).
	•	Store to be assigned (por asignar).
	•	Mantenimiento:
	•	Fallas críticas (refrigerador detenido).
	•	Alertas preventivas (funciona pero show de cuidado).
	•	Atendidos (ya pasó técnico).
	2.	Fallas específicas
	•	High Temperature: supera el umbral inteligente según modelo.
	•	Failure associated with compressor: patrón anómalo en % de trabajo del compresor.
	•	Possible electrical damage: voltaje fuera de rango (muy alto/bajo).
	3.	Alertas en tiempo real
	•	High compressor working time: compresor encendido sin parar por horas (riesgo de que no enfríe).
	•	High temperature alert: picos de temperatura (> umbral).
	•	Low/High voltage: fluctuaciones peligrosas de voltaje.
	•	High temperature from voltage: temperatura alta atribuible al voltaje.
	•	High temperature due to disconnection: subidas de temperatura por desconexión breve.
	•	Working time: uso continuo excesivo (mantenimiento preventivo).
	4.	CLT (Cooler Life Tracking)
	•	Detalle de cada enfriador: identificador, modelo, zonas, rutas, estado actual (ej. “Working with Alert”).
	•	Actividad histórica:
	•	Registro cronológico de eventos (control de activos, alertas, órdenes de servicio).
	•	Fechas y descripciones de fallas / mantenimientos.
	•	Mapa de ubicación:
	•	Dirección registrada vs. ubicación real (distancia en metros).
	•	Historial de movimiento (última vez y punto de venta asignado).
	•	Costo total de propiedad (sin energía):
	•	Costo original del enfriador + costo acumulado de órdenes de servicio (OS).
	•	Consumo energético:
	•	KW/h promedio y costo estimado ($ MXN), separado para análisis.
	5.	Coolview (dentro de CLT)
	•	Gráficas de telemetría (línea de tiempo): temperatura, voltaje, % compresor, % puerta abierta.
	•	Eventos superpuestos en la gráfica (alertas, desconexiones, órdenes de servicio).
	•	Permite hacer zoom y correlacionar picos o anomalías con acciones puntuales en campo.

⸻

¿Cómo ayuda?
	•	Visibilidad total del parque de enfriadores (ubicación, estado, rendimiento).
	•	Detecta a tiempo anomalías en temperatura, voltaje o compresor para prevenir pérdidas de productos.
	•	Prioriza mantenimientos y órdenes de servicio basadas en datos reales:
	•	Evita visitas innecesarias.
	•	Enfoca recursos donde generan mayor impacto (equipos con mayor riesgo).
	•	Calcula el TCO (sin energía) para decidir si conviene mantener o reemplazar un equipo.
	•	Analiza consumo energético para optimizar eficiencia o renegociar tarifas eléctricas.
	•	Mide el desempeño de tu equipo de preventas (visitas exitosas vs. programadas).
	•	Sirve como fuente de verdad única para ver tendencias históricas y justificar inversiones.

⸻

Beneficios clave
	1.	Menos tiempo de inactividad
	•	Las alertas inteligentes (umbral adaptativo por modelo) permiten reaccionar antes de que el refrigerador se detenga.
	2.	Reducción de costos de mantenimiento
	•	Con diagnósticos basados en telemetría real, se evita el overmaintenance y se extiende la vida útil del equipo.
	3.	Optimización de rutas y cobertura
	•	Monitoreo de rutas de preventas y % de cobertura real vs. esperada (discrepancias < 50 m).
	4.	Toma de decisiones basada en datos
	•	Con TCO + consumo energético vs. energía real, se evalúa si conviene reparar o remplazar.
	•	Identifica puntos de venta con baja rotación (no sale) para reasignar o reactivar.
	5.	Informe y trazabilidad
	•	Historial completo de todos los eventos por enfriador.
	•	Transparencia para auditorías internas y externas (p. ej. para cumplir SLAs con Trueque de refrescos).
	6.	Escalabilidad y flexibilidad
	•	Soporta cientos de miles de enfriadores distribuidos por región / zona / ruta.
	•	Filtros jerárquicos tipo “explorador de carpetas” para llegar desde “México completo” hasta “el refri de la taquería cercana”.
	•	Actualización de datos cada hora (picos de movimiento de preventas generan más actividad).

⸻

¿Por qué Solkos Consola y no solo Excel?
	1.	Datos en tiempo real (casi)
	•	Cada hora se refresca la telemetría; en Excel tendrías que importar manualmente y perderías contexto.
	2.	Visualización geoespacial
	•	Mapa interactivo con zonas coloreadas por región.
	3.	Alertas y notificaciones
	•	Desencadena órdenes de servicio sin revisar doc tras doc.
	4.	Análisis histórico y predictivo
	•	Los umbrales adaptativos por modelo permiten predecir fallas antes de que ocurran.
	5.	Costo vs. valor
	•	El costo de ignorar una alerta puede representar miles de pesos en mercadería echada a perder.

⸻

Preguntas de futuro
	•	¿Cómo agregaríamos el costo energético dentro del TCO sin sobrecargar la UI?
	•	¿Qué otros KPIs de negocio (ventas, rotación de producto) podíamos cruzar para dar insights más amplios?
	•	¿Conviene extender Consola a otros equipos (vitrinas, aires acondicionados, unidades de refrigeración chica)?
	•	¿Qué modelo de machine learning podríamos entrenar con toda esa telemetría para predecir vida útil restante con mayor precisión?

⸻

Nota final: Solkos Consola no es solo un tablero: es la espina dorsal para la operación inteligente de flotas de enfriadores. Permite pasar de “¿qué le pasa a mi refri?” a “sé exactamente qué hacer y cuándo”.

⸻

Resumen rápido para compartir (sin formalidades)
Solkos Consola es la plataforma online que junta toda la telemetría de tus refrigeradores, la dibuja en mapas y gráficas, y te avisa con alertas inteligentes cuándo un equipo va a fallar.
Está pensada para marcas como Coca-Cola, Heineken o Lala, que tienen miles de enfriadores en tiendas, Oxxos y mercados.
Con Consola ves de un vistazo:
	1.	Si tus enfriadores están donde deben estar.
	2.	Cuáles no venden y necesitan visita extra.
	3.	Alertas de temperatura, compresor y voltaje.
	4.	Historial completo y costos de mantenimiento.
	5.	Consumo energético para saber cuánto te cuesta la luz.

Beneficio: evitar pérdidas de producto, reducir visitas innecesarias, prolongar la vida útil de tus refri y tener toda la información de tu flota en un solo lugar.
---
Hoja de Producto: Coolector
Hoja de Producto: Coolector

¿Qué es?App móvil que, vía Bluetooth y GPS, extrae telemetría de controladores Imbera y la manda al backend en ~10–15 min para que Consola la muestre.

¿Para quién?• Preventas (camiones de Coca-Cola, Heineken, etc.)

¿Qué hace?• Conecta con el controlador BT del refri• Captura: temperatura, voltaje, % compresor, apertura de puertas + ubicación• Envía telemetría al backend apenas la lee• Sirve de puente para activar/desactivar Vault

Problemas técnicos que resuelve• Unifica varios SDKs de controladores distintos (versiones/proveedores)• Gestiona incompatibilidades de Bluetooth• Maneja casos de señal inestable: reintentos automáticos• Procesa datos con latencia mínima para que Consola esté al día

Retos actuales• SDKs mal documentados y no optimizados (ingeniería inversa limitada)• Dependencia de permisos (Bluetooth, GPS, Internet) en el celular• Variabilidad entre modelos de refri que a veces bloquea la lectura

Solución de producto (features clave)
Lectura inteligente• Ciclo de reintentos hasta obtener telemetría completa• Notificación si lleva X seg sin conexión para forzar reintento
Ubicación fiable• Usa GPS del celular en cuanto detecta BT del refri (< 50 m)• Almacena offline si no hay internet y reintenta al restablecerse
Módulo Vault• Recibe señal de Consola para “inmovilizar” refri• Envía confirmación cuando controlador entra en modo Vault
Coolector+ (en desarrollo)• Sistema de recompensas/gamificación para incentivar lecturas• Rankings semanales de preventas con mejor cobertura y lecturas exitosas

Flujo de datos
Preventa abre Coolector con BT+GPS activos.
App busca refri cercano, extrae telemetría.
Envía datos al backend; aparece en Consola ~10–15 min después.
Si Consola manda Vault a ese refri, Coolector envía la señal al controlador.

Integraciones clave• SDK controladores: varias versiones de proveedores (compatibilidad)• GeoAPI: validación de ubicación vs. dirección registrada (≤ 50 m)• Backend Solkos: ingestión y procesado en tiempo real• Consola: consumo de datos y envío de señal Vault

Beneficios clave
Cobertura más alta: datos frescos cada ruta
Reducción de errores de lectura: reintentos y offline guardan telemetría
Acción rápida: Consola ve datos en 15 min y envía Vault o alerta
Preparado para gamificación: Coolector+ incentivará al preventa a mantener permisos activos

Resumen rápidoCoolector es el “scanner” en cada ruta de preventa que, sin complicarte, lee y sube la telemetría de los refri. Maneja SDKs distintos, falla menos con reintentos y pronto recompensará a los preventas más eficientes con Coolector+.

---
Hoja de Producto: Cooltech
¿Qué es?App Android todo‑en‑uno para técnicos de Repare: recolección, diagnóstico y control en campo.
¿Para quién?
Técnicos de servicio en PYMEs
Técnicos de Repare
Equipos de mantenimiento de enfriadores Imbera
¿Qué hace?
Recolecta telemetría (Coolector)
Monitorea variables clave (mini‑CLT)
Muestra histórico de datos (mini‑Coolview)
Lista últimas órdenes de servicio
Recomienda plan de acción (Cooldetect)
Controla el refri: firmware y test de componentes
Problemas técnicos que resuelve
Diagnóstico empírico lento y poco fiable
Falta de contexto histórico para decisiones
Esperas largas en generación de recomendaciones
Retos actuales
Reducir la latencia del diagnóstico de minutos a segundos
Garantizar compatibilidad y seguridad al cambiar firmware
Optimizar UI/UX para uso rápido bajo presión
Solución de producto (features clave)
Mini‑CLT: vista instantánea de temperatura, voltaje y compresor
Mini‑Coolview: histórico gráfico de variables críticas
Cooldetect: IA que sugiere pasos de reparación basados en casos previos
Control remoto: modo prueba y actualización de firmware desde el móvil
Flujo de datos
Técnico conecta vía Bluetooth al enfriador
App extrae telemetría y órdenes asociadas
Coolview y Cooldetect procesan datos
Técnico ve recomendaciones y ejecuta tests o firmware
Integraciones clave
SDKs BT de controladores (Imbera y terceros)
Backend Solkos (ingestión, órdenes y ML)
Base de datos de historial de servicio
Beneficios clave
Diagnóstico basado en datos, no en suposiciones
Historial y recomendaciones al instante
Control y test de piezas desde el celular
Resumen rápidoCooltech es la navaja suiza del técnico de Repare: lee, diagnostica y controla tu enfriador en segundos.

---
Hoja de Producto: Negocon
¿Qué es?App Android que actúa como mini CLT móvil de Consola.
¿Para quién?
Dueños de tienditas, restaurantes, pastelerías… (clientes detallistas)
PYMEs que usan enfriadores Imbera
¿Qué hace?
Muestra salud y telemetría del refri
Recoge datos sin esperar al preventa
Cambia modos (carne, lácteos, refrescos, ahorro)
Problemas técnicos que resuelve
Punto de recolección lejano
Unifica compatibilidad básica con varios SDK BT
Retos actuales
Ausencia de propuesta de valor clara para el usuario final: ¿por qué abrir la app sin un gancho?
Mantenimiento esporádico y atrasado vs Coolector
Solución de producto (features clave)
Telemetría móvil: feed CLT en tiempo real
Control bidireccional (solo Imbera no marca): comandos de modo
Modo solo lectura (KOF/Heineken): CLT restringido
Flujo de datos
Usuario activa BT y conecta al refri
Negocon extrae y muestra métricas
Datos se envían al backend Solkos
Integraciones clave
SDKs de controladores BT (Imbera y proveedores)
Consola/Backend Solkos
API de GPS para ubicación
Beneficios clave
Cobertura inmediata sin preventa
Control directo al empresario
Monitor en tu bolsillo
Resumen rápidoNegocon lleva la consola al celular del dueño, recolecta telemetría y controla el refri al instante.

---
Hoja de Producto: Solkos Intelligence
¿Qué es?: Capa de IA (Agentes) en WhatsApp/Chat.
Qué es?Capa de IA multi‑agente encima de Coolector, Negocon, Cooltech y Consola, que añade canales conversacionales (principalmente WhatsApp) para automatizar acciones operativas sin intervención humana.
¿Para quién?• Supervisores de rutas y preventas• Técnicos de Repare• Dueños de PYMEs (tienditas, restaurantes)• Equipo de atención y postventa
¿Qué hace?• Asigna y prioriza visitas operativas (Agente Operativo)• Gestiona reportes y cierra órdenes de servicio (Agente Repare)• Permite consultas CLT vía chat (Agente CLT)• Envía encuestas de satisfacción post‑servicio (Agente Satisfacción)• Automatiza notificaciones y seguimientos en WhatsApp
Problemas técnicos que resuelve• Dependencia de supervisión manual y múltiples herramientas• Fragmentación de procesos entre apps y canales• Retrasos en detección de enfriadores sin lectura• Falta de trazabilidad en órdenes de servicio
Retos actuales• Entrenar agentes con datos heterogéneos de telemetría y órdenes• Asegurar seguridad y privacidad en WhatsApp• Escalar rendimiento de IA en tiempo real• Fomentar adopción del canal conversacional por usuarios
Solución de producto (features clave)
Agente Operativo: responde “¿Qué equipos revisar hoy?” con lista priorizada.
Agente Repare: reporta, valida y cierra órdenes desde el chat.
Agente CLT: muestra telemetría clave (temp., voltaje, compresor).
Agente Satisfacción: envía encuestas automáticas tras el servicio.
Flujo de interacción
Supervisor escribe “¿Qué tengo que revisar hoy?” en WhatsApp.
Agente Operativo entrega lista y criterios de prioridad.
Técnico reporta falla: Agente Repare valida datos y crea orden.
Usuario/personal consulta CLT con Agente CLT en cualquier momento.
Tras cierre, Agente Satisfacción lanza encuesta y recopila feedback.
Integraciones clave• API de Consola/Backend Solkos (activos, telemetría, órdenes)• WhatsApp Business API• Base de datos de historial de servicio y ML• Sistemas de geolocalización y ruteo
Beneficios clave
Flujo operativo completamente automatizado
Menos fricción y errores manuales
Mayor cobertura y puntualidad en lecturas
Mejor trazabilidad y satisfacción del usuario
Resumen rápidoSolkos Intelligence es la capa de IA que, mediante agentes conversacionales en WhatsApp, automatiza asignaciones, reportes, consultas CLT y encuestas, optimizando la eficiencia operativa sin necesidad de un operador humano.

---
"""

def get_full_context():
    return f"EQUIPO:\n{TEAM_MEMBERS}\n\nPROJECT PRODUCT SHEETS:\n{PROJECTS_CONTEXT}"
