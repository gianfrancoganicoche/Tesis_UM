# Módulo de modelos no lineales

Todo lo relacionado con la pregunta del tutor: **¿un modelo no lineal se comporta mucho mejor que el lineal?** El valor de un jugador es comportamiento humano y puede no ser lineal en edad, contexto o rendimiento. Este módulo no reemplaza al modelo bayesiano jerárquico (`../modelado/`): lo usa como base de comparación y, si hace falta, lleva la flexibilidad adentro de ese modelo.

El documento con los resultados vive aparte en `entregables/modelo_no_lineal/`. No forma parte del documento de avance para el tutor.

## Escalera de pasos

Se sube de escalón solo si el anterior lo justifica.

| Paso | Script | Qué responde | Estado |
|---|---|---|---|
| 1 | `nl01_predicciones_lineal.py` | Predicciones del modelo lineal en jugadores nuevos, por pliegue | Listo para correr |
| 2 | `nl02_referente_boosting.py` | ¿Un gradient boosting predice jugadores nuevos mejor que el lineal? | Listo para correr |
| 3 | `nl03_diagnostico_no_lineal.py` | ¿Dónde y por qué gana el boosting? Error por segmento, no linealidad contra interacciones, importancia por permutación y dependencia parcial por posición | Listo para correr |
| 4 | `nl04_extensiones_bayesianas.py` | Splines e interacciones dentro del modelo bayesiano (minutos × rendimiento, splines en edad de debut y goles recibidos, cola de edad), con ΔELPD contra el lineal | Listo para correr |
| 5 | `nl05` (pendiente) | BART (`pymc-bart`), solo si el 4 no alcanza | Pendiente |

## Cómo correrlo

```
uv run scripts/modelo_no_lineal/nl01_predicciones_lineal.py --temporada rw --objetivo-aceptacion 0.97 --tune 2000 --draws 2000 --etiqueta lineal_rw
uv run scripts/modelo_no_lineal/nl02_referente_boosting.py --etiqueta lineal_rw
```

```
uv run scripts/modelo_no_lineal/nl03_diagnostico_no_lineal.py --etiqueta lineal_rw_sin_ctx --excluir-variables ctx

# nl04: extensiones dentro del modelo bayesiano (6 modelos x 5 pliegues; usar --rapido para probar)
uv run scripts/modelo_no_lineal/nl04_extensiones_bayesianas.py --temporada rw --mundlak --objetivo-aceptacion 0.97 --tune 2000 --draws 2000 --etiqueta ext_rw_mun
```

`nl01` ajusta el modelo lineal cinco veces (un ajuste por pliegue) y tarda como un contraste de H1 con tres modelos dividido tres (unos 25 a 40 minutos). `nl02` tarda pocos minutos. Con `--rapido` ambos hacen una prueba de humo.

## Control de fuga: `companieros_valor_promedio`

Esa variable es el promedio del valor de los compañeros **sin el propio jugador**: (T − v_i)/(N − 1), con T el valor total del plantel y N su tamaño. Dentro de un club-temporada, T y N son iguales para todos, así que la variable queda ligada de forma mecánica al valor propio v_i. El lineal casi no puede aprovecharlo (v_i entra dividido por N − 1), pero un modelo flexible reconoce el club-temporada con las otras variables de contexto, aprende T de los compañeros que están en entrenamiento y despeja v_i.

Con la prueba de humo (3 pliegues, grilla mínima, RMSE en jugadores nuevos) se midió la diferencia:

| Variables que usan ambos modelos | Lineal | Boosting | Mejora |
|---|---|---|---|
| Todas | 1,097 | 0,750 | 32 % (fuga) |
| Sin `companieros_valor_promedio` | 1,227 | 1,071 | 12,7 % |
| Sin nada de contexto | 1,336 | 1,240 | 7,2 % |

Por eso la comparación válida es la que **no** usa esa variable (y, como segundo control, la que no usa contexto). Para que lineal y boosting usen las mismas variables:

```
uv run scripts/modelo_no_lineal/nl01_predicciones_lineal.py --quitar-variable companieros_valor_promedio --etiqueta lineal_rw_sin_comp
uv run scripts/modelo_no_lineal/nl02_referente_boosting.py --etiqueta lineal_rw_sin_comp --excluir-variables companieros_valor_promedio
uv run scripts/modelo_no_lineal/nl01_predicciones_lineal.py --quitar-contexto --etiqueta lineal_rw_sin_ctx
uv run scripts/modelo_no_lineal/nl02_referente_boosting.py --etiqueta lineal_rw_sin_ctx --excluir-variables ctx
```

Queda para discutir con el tutor construir esa variable con el plantel de la temporada anterior o al inicio de la temporada, para cortar el vínculo mecánico con el valor del jugador.

## Diseño de la comparación

- **Mismas filas y mismos pliegues** que el contraste de H1 (`m03`): cinco pliegues por jugador con semilla 2026. Todas las filas de un jugador van al mismo pliegue, así que se evalúa sobre jugadores que el modelo no vio.
- **Mismas variables**: edad, posición, temporada, contexto, rendimiento y atributos. Con `--mundlak` en `nl01` y `--medias-jugador` en `nl02`, ambos reciben además los promedios por jugador.
- **Sin efecto individual**: ninguno de los dos modelos conoce el nivel propio de un jugador nuevo. El lineal predice la parte fija (efecto individual igual a cero) y el boosting predice el valor esperado dado las variables.
- **Hiperparámetros del boosting** elegidos solo con los datos de entrenamiento de cada pliegue (validación cruzada interna agrupada por jugador). El pliegue de prueba nunca participa de la elección.
- **Métrica**: RMSE, MAE y R² en jugadores nuevos, y la diferencia de error cuadratico medio por jugador con su error estándar (regla de 2 SE, igual que el ΔELPD). La unidad de evaluación es el jugador y no la fila.

## Cómo leer el resultado de nl02

- **El boosting no mejora de forma clara, o mejora poco** (del orden de 1 a 2 % en RMSE): la forma lineal no es una limitación relevante para predecir. La conclusión para la tesis es que se probó una alternativa mucho más flexible y no gana, y por eso se mantiene el modelo lineal, que es más fácil de interpretar.
- **El boosting mejora de forma clara y de tamaño relevante**: hay estructura no lineal o interacciones que el lineal pierde. Se pasa al paso 3 para ver dónde y al paso 4 para incorporarlo al modelo bayesiano.
- **El boosting empeora**: es posible cuando la señal es mayormente lineal y el ruido es grande, porque un modelo flexible ajusta ruido. Tampoco es evidencia a favor de lo no lineal.

## Límites que conviene tener presentes

- El boosting da predicciones puntuales y no una densidad predictiva, así que no se compara con ELPD sino con error de predicción. `nl01` guarda también el ELPD por jugador del lineal para compararlo después con los splines bayesianos del paso 4.
- Casi la mitad de la varianza no explicada es el efecto individual de cada jugador, que ningún modelo con estas covariables puede predecir en un jugador nuevo. Por eso es esperable que las mejoras de RMSE sean chicas aunque exista no linealidad.
- Un resultado de predicción no es un resultado causal: cualquier mejora del boosting dice algo sobre la forma de la relación y no sobre el efecto del club.
