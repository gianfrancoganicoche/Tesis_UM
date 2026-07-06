# Bitácora — Entrada 1: Definición del tema y elección de tutor / Hallazgo crítico de datos

**Fecha:** 29/06/2026

*Este documento registra el proceso de definición y desarrollo de la tesis en orden
cronológico. La idea es no perder de vista las decisiones tomadas, por qué se tomaron, y
qué quedó pendiente — para no repetir razonamientos ni perder detalles importantes con el
paso del tiempo.*

## Parte A — Del problema disperso al tema definitivo

### Punto de partida

Maestría en Ciencia de Datos, interés en aplicar el trabajo a deportes, específicamente
fútbol (por mercado e interés propio). Dos grandes candidatos iniciales: predicción de
partidos, o scouting con datos.

### Recorrido de descarte (resumen)

- **Predicción de partidos** → descartado como tema central por estar saturado
  académicamente. Queda como proyecto personal a futuro (ver sección final).
- **Scouting con datos en general** → demasiado amplio, había que acotar.
- **Predicción de rendimiento al transferirse entre ligas** (league adjustment) → tema
  atractivo, pero con problema de datos serio para Latinoamérica.
- **Identificar jugadores subvalorados respecto al valor de mercado** → descartado al
  razonar que Transfermarkt YA es un consenso de expertos; un modelo propio difícilmente
  le "gane" al mercado sin información privilegiada.
- **Aislar calidad individual del efecto de equipo/liga + predecir desarrollo de
  jóvenes** → tema definitivo. Conjuga econometría, scouting de talento joven, y el
  objetivo laboral real.

### Tema definitivo

> **Pregunta de investigación central**
> ¿Es posible predecir la trayectoria de desarrollo de jugadores jóvenes de fútbol a
> partir de métricas de rendimiento tempranas ajustadas por contexto de equipo y liga,
> usando el crecimiento de valor de mercado (Transfermarkt) como variable dependiente?

*(Nota: esta pregunta se refinó posteriormente — ver Entrada 2, 05/07/2026.)*

### Por qué este tema (razones clave)

- Resuelve algo que el scouting humano no puede hacer bien: aislar sistemáticamente
  cuánto del rendimiento observado es mérito del jugador vs. del equipo/liga.
- Tiene un enfoque econométrico fuerte (estimador de efectos fijos sobre datos de
  panel) — esto es lo que le da el salto de calidad metodológico.
- Datos públicos y accesibles para ligas europeas (con la salvedad de la Parte B, sobre
  FBref).
- Conecta con el objetivo laboral real: trabajar en un club identificando talento joven
  (modelo de negocio tipo Ajax/AZ Alkmaar).

### Decisión clave de variable dependiente

Se discutió y descartó usar "desarrollo técnico" como variable (poco medible). Se optó
por crecimiento de valor de mercado en Transfermarkt entre T y T+3 para jugadores
sub-23, por ser estándar, verificable, y alineado con cómo el mercado real mide el éxito
de una apuesta de desarrollo de talento.

### Limitación aceptada explícitamente — Latinoamérica

> **Decisión consciente**
> La tesis vive en ligas europeas por disponibilidad de datos. Se evaluó pagar acceso a
> Wyscout/InStat para incluir Uruguay/Sudamérica (~200-500 EUR/mes) y se decidió NO
> hacerlo: si la metodología funciona en Europa, debería ser transferible a cualquier
> mercado cuando existan datos. Se documenta como limitación y como motivación para
> trabajo futuro, no como falla del diseño.

### Metodología (esquema acordado en esta etapa)

- **Etapa 1** — Estimador de efectos fijos para aislar calidad individual (α_i) del
  efecto de equipo (γ_j) y liga, con regularización/shrinkage para jugadores con pocos
  minutos (análogo a RAPM de basketball).
- **Etapa 2** — KPIs diferenciados por posición (el efecto de equipo se manifiesta
  distinto según el rol: delanteros, mediocampistas, defensores, laterales).
- **Etapa 3** — Modelo predictivo (XGBoost/Random Forest) del crecimiento de valor de
  mercado a 3 años, usando las métricas ajustadas como features.

### Tutor — proceso de selección

Se revisó el listado oficial de tutores de la Maestría (UM/UMPE). Se identificaron dos
candidatos por su perfil económico/econométrico:

| Candidato | Por qué | Estado |
|---|---|---|
| Alan Silberman | Doctorando en Cs. Económicas (UBA), Lic. en Economía. Único del listado con "Deportes" como área de interés declarada. | Contactado por mail. Documento de tema enviado. Esperando respuesta. |
| Javier Burroni | Actuario + Master Economía (Di Tella) + PhD Machine Learning (UMass Amherst). Sin interés en deportes declarado — requiere pitch más técnico. | Plan B si no hay respuesta de Silberman en ~14 días. |

### Plan de contacto

- Día 0 — Mail enviado a Silberman con pitch personalizado (deportes + economía).
- Día +1 — Documento de tema (versión punteo) enviado.
- Día ~7 sin respuesta → mandar seguimiento corto.
- Día ~12-14 sin respuesta o respuesta negativa → contactar a Burroni con pitch técnico
  (identificación causal con datos de panel).

### Proyecto personal en paralelo (no forma parte de la tesis)

Predicción de partidos orientada a mercados de apuestas — específicamente identificar
heterogeneidad en la eficiencia del mercado según contexto (ligas menores, mercados
secundarios poco líquidos como córners/tarjetas, sesgos del apostador promedio). Se
descarta como tema de tesis por tener menor credibilidad académica ante un comité, pero
queda anotado como posible contenido de portfolio/blog técnico a futuro.

## Parte B — Hallazgo crítico de datos: corte FBref/Opta

### Qué pasó

> **Hecho relevante (20 de enero de 2026)**
> Stats Perform (empresa de Opta) terminó el acuerdo de datos con FBref y exigió
> eliminar todas las estadísticas avanzadas del sitio. El motivo aparente: Opta fue
> designado distribuidor exclusivo de datos de apuestas para el Mundial 2026, lo que
> entró en conflicto con seguir cediendo esos mismos datos gratis. Como resultado, xG,
> xA, progressive passes, pressures y demás métricas avanzadas ya no están disponibles
> en FBref en vivo.

### Impacto en la tesis

FBref sigue existiendo para datos básicos (goles, asistencias, minutos) pero perdió todo
lo "avanzado" que era clave para el diseño original. Esto no mata el proyecto, pero
obliga a reorganizar de dónde sale cada dato.

### Solución encontrada

| Necesidad | Fuente alternativa | Nota |
|---|---|---|
| Métricas avanzadas históricas (xG, progressive passes, etc.) para el año T de jugadores jóvenes | Datasets de Kaggle scrapeados de FBref antes del corte (ej. `hubertsidorowicz/football-players-stats`, por temporada) + repo GitHub `eddwebster/football_analytics` | Como el modelo usa ventana T→T+3, no se necesita data en vivo: alcanza con fotos históricas ya capturadas pre-enero 2026. |
| xG actualizado / en vivo (si se necesitara en el futuro) | Understat (gratuito, 5 grandes ligas, sin progressive passes) | Cobertura más limitada que FBref pre-corte pero gratuita y activa. |
| Valor de mercado evolutivo (variable dependiente) | Transfermarkt vía Kaggle (`davidcariboo/player-scores`) | No depende de Opta. No afectado por el corte. Actualización semanal automática. |
| Datos de eventos completos (si se ataca un enfoque más granular) | StatsBomb Open Data | Fuente completamente separada de Opta. No afectada. |

### Decisión tomada

- Se trabaja con ventanas históricas pre-corte (ej. temporada base 2019-2020 o
  2020-2021) para la variable T, dato que ya está capturado y circulando en datasets
  públicos.
- Transfermarkt sigue siendo la fuente de la variable dependiente sin cambios — no
  afectado por el incidente.
- Se documenta el incidente en la sección de fuentes de datos de la tesis como
  evidencia de un riesgo estructural real del campo (dependencia de licencias de
  terceros), no como improvisación.

*(Nota: esta decisión se profundizó más adelante — el pivot terminó siendo más completo
de lo previsto acá: en vez de combinar FBref histórico + Transfermarkt, la tesis pasó a
apoyarse principalmente en `davidcariboo/player-scores`, que también incluye apariciones
básicas. Ver Entrada 3, 05/07/2026.)*

## Próximos pasos pendientes (al cierre de esta entrada)

- Esperar respuesta de Alan Silberman (seguimiento día ~7, plan B día ~14).
- Terminar de leer los 3 papers centrales: Transfer Portal (arXiv 2201.11533),
  Plus-Minus Soccer (arXiv 1706.04943), Large Event Models (arXiv 2402.06815).
- Bajar y explorar manualmente un dataset de Kaggle con métricas avanzadas históricas
  (hubertsidorowicz o similar) para confirmar cobertura real de columnas y temporadas.
- Bajar y explorar el dataset de Transfermarkt (`davidcariboo/player-scores`) y
  verificar granularidad temporal del valor de mercado por jugador.
- Definir alcance final de ligas a incluir (sugerido: Eredivisie, Liga Portuguesa,
  Bundesliga, Premier League como referencia de mercado top).
