# Para la próxima tutoría — plan de trabajo sobre la Alternativa 3

*Documento breve para discutir en la reunión. Detalle técnico completo en
`docs/hipotesis_y_diseno_v2.md`.*

## El plan

Voy a centrar el desarrollo de la tesis en la Alternativa 3: descomposición del valor
de mercado en curva de edad + contexto (liga, equipo) + habilidad individual (α_i),
sobre trayectorias completas de carrera en vez de pares fijos T→T+3.

### Lo que se puede hacer ya, con los datos actuales

**Pregunta ancla, testeable con sí/no:**
> H1a: El contexto de equipo y liga explica una porción estadísticamente significativa
> de la varianza en el valor de mercado de jugadores sub-23 de las 5 grandes ligas
> europeas, más allá de lo que explica la curva de desarrollo por edad.

**Cómo se testea:** test de razón de verosimilitud entre un modelo restringido (solo
curva de edad + efecto individual) y el modelo completo (+ efectos de contexto). H0: la
varianza del componente de contexto es cero. Es el mismo tipo de test formal que un test
F de significancia conjunta — no es una comparación de RMSE entre dos modelos de
machine learning, es un test de hipótesis clásico con p-valor.

**H2** (ya estaba, se mantiene igual): el efecto del contexto varía según la posición —
testeado con la misma lógica de modelos anidados (interacción edad×posición).

**Por qué se acota a las 5 grandes ligas para el test ancla:** es donde la densidad y
calidad de datos es máxima (confirmado en sesiones anteriores — cobertura de contexto,
score de prestigio de liga, etc. son más confiables ahí). Empezar ahí da un resultado
sólido rápido, sin comprometer el alcance completo de la tesis.

### Cómo se extiende a partir de ahí

**H1b:** ¿el efecto encontrado en H1a se sostiene, se atenúa, o cambia al extender el
análisis a ligas secundarias? ¿Varía con el nivel de concentración/calidad de la liga?
Mismo tipo de test formal (interacción liga-tier × contexto), corrido como extensión
de robustez una vez que H1a esté resuelto. Esto además resuelve el punto 4 de la
devolución original (validez entre ligas concentradas) en vez de dejarlo aparte.

**Por qué esto no es "elegir T+3 con otro nombre":** a diferencia del diseño original,
acá no hay una ventana de predicción fija que buscar — el modelo estima la curva de
edad completa, y el horizonte de interés (¿cuánto vale a los 22? ¿a los 24?) es una
consulta libre sobre esa curva ya ajustada, no un parámetro que hay que optimizar de
antemano.

## Las otras dos alternativas (para mencionar, no para desarrollar)

No las descarto, pero no las voy a desarrollar en paralelo — las dejo anotadas por si
prefieren discutirlas como variantes o como robustez adicional más adelante:

- **Alternativa 1** (comparación A/B, ajustada para buscar el horizonte T óptimo
  empíricamente en vez de fijarlo en T+3): la más fiel al planteo original de la
  devolución, pero con el riesgo de que la comparación de RMSE entre modelos sea poco
  informativa si un modelo simplemente tiene más variables.
- **Alternativa 2** (feature importance / SHAP sobre un modelo único): evita ese riesgo,
  pero no aísla una señal de calidad individual portable, y la importancia de SHAP no
  es evidencia causal en sentido estricto.

## Cuadro resumen

| | Alternativa 1 (A/B) | Alternativa 2 (SHAP) | Alternativa 3 (descomposición, el plan) |
|---|---|---|---|
| Usa trayectorias completas | Sí | Sí | Sí |
| Busca horizonte T óptimo como paso previo | Sí | Sí | No aplica — el horizonte es una consulta libre sobre la curva ya ajustada |
| Qué responde | ¿El ajuste por contexto mejora la predicción? | ¿Qué variables de contexto importan más? | ¿El contexto explica varianza significativa, más allá de la edad? + score portable por jugador |
| Test de hipótesis clásico (p-valor) | No — comparación de error predictivo | No — importancia predictiva, no inferencial | Sí — test de razón de verosimilitud, modelos anidados |
| Riesgo de resultado poco informativo | Alto (más variables casi siempre "gana") | Bajo | Bajo |
| Interpretabilidad causal | Alta (experimento controlado) pero sin formalidad estadística clásica | Media (predictiva, no causal) | Media-alta (estructural, con supuestos testeados explícitamente) |
| Usable directo para scouting | Bajo | Medio | Alto — score α_i portable entre contextos |
| Complejidad de implementación | Baja-media | Media | Alta — requiere la curva de edad bien estimada antes de avanzar |
| Fidelidad al planteo original de Alan | Total | Parcial | Menor en la forma, pero da el tipo de test formal que un tribunal reconoce |

## Bibliografía de respaldo (actualizada para este enfoque)

Se agregaron tres papers que no estaban cubiertos y sostienen directamente la curva de
edad: Dendir (2016) y Kalén et al. (2019) confirman la forma esperada de la curva
(pico 25-27 general, arqueros/centrales más tarde) tanto en rendimiento como en valor
de mercado; Säfvenberg et al. (2024) es el precedente metodológico más cercano —
literalmente el mismo tipo de modelo jerárquico con shrinkage por jugador que se
planea usar acá, aplicado a una liga de menor nivel. Detalle completo en
`docs/bibliografia.md`.

## Lo que necesito de esta reunión

1. Validación del plan: H1a como pregunta ancla, extensión a H1b para ligas
   secundarias, dejando Alternativas 1 y 2 como mención para más adelante.
2. Su opinión sobre acotar el test inicial a las 5 grandes ligas — ¿de acuerdo con el
   orden (ancla primero, extensión después), o prefiere que se incluya todo desde el
   principio?
3. Prioridad entre los puntos pendientes de su devolución original (validez entre
   ligas concentradas — ahora parte de H1b; calidad de datos por país/año; survivorship
   bias) — ¿alguno bloquea el avance con el plan de arriba?
