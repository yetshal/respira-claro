# Diccionario de predicados de RespiraClaro

Referencia de los predicados de `base_conocimiento.pl`. Está organizado siguiendo el recorrido de una consulta: primero los hechos y reglas que alimentan al motor, luego la inferencia, después la explicabilidad ("¿Por qué?") y la recomendación ("¿Qué falta?"), y al final los auxiliares.

## Cómo leer las firmas

| Símbolo       | Significado                                     |
| ------------- | ----------------------------------------------- |
| `+`           | Entrada: debe llegar instanciado                |
| `-`           | Salida: llega libre y el predicado lo instancia |
| `?`           | Puede usarse como entrada o como salida         |
| `Predicado/N` | Predicado con N argumentos (aridad)             |

---

## 1. Hechos y reglas base

### `sintoma_enfermedad/3`

```prolog
sintoma_enfermedad(+Sintoma, +Enfermedad, -Peso)
```

Dice cuánta evidencia aporta un síntoma a favor de una enfermedad. El peso va de 1 a 4, y el 0 tiene un significado especial:

- 1: evidencia baja, el síntoma es inespecífico.
- 2: evidencia media.
- 3: evidencia alta.
- 4: muy alta o patognomónico.
- 0: excluyente. Si el síntoma está presente, la enfermedad se descarta.

```prolog
sintoma_enfermedad(perdida_olfato, covid, 4).    % patognomónico de COVID
sintoma_enfermedad(fiebre, alergia, 0).          % la alergia no da fiebre
sintoma_enfermedad(congestion, resfriado, 4).    % muy característico del resfriado
```

### `sintoma_peso/2`

```prolog
sintoma_peso(+Sintoma, -PesoGlobal)
```

Prioridad global de un síntoma al momento de decidir qué preguntar. Es independiente de cualquier enfermedad en particular y va de 2 a 10. Cuanto más alto, antes se pregunta.

```prolog
sintoma_peso(fiebre, 10).              % separa la alergia (que la excluye) del resto
sintoma_peso(perdida_olfato, 9).       % muy específico de COVID
sintoma_peso(dificultad_respirar, 8).  % indica gravedad y es bastante específico
sintoma_peso(fatiga, 2).               % aparece en casi todo
```

### `regla/5`

```prolog
regla(+ReglaID, +CondicionesPositivas, +CondicionesNegativas, +Conclusion, +Descripcion)
```

Una regla de diagnóstico completa:

- `ReglaID`: átomo único que identifica la regla (por ejemplo `r1_gripe`).
- `CondicionesPositivas`: síntomas que deben estar presentes.
- `CondicionesNegativas`: síntomas que no deben estar presentes. Si no hay, va `[]`.
- `Conclusion`: la enfermedad que se diagnostica.
- `Descripcion`: texto legible que se muestra en la explicación.

```prolog
regla(r8_alergia, [congestion, estornudos], [fiebre], alergia,
      'Rinitis alérgica: congestión + estornudos + SIN fiebre').
regla(r5_covid, [fiebre, tos, perdida_olfato], [], covid,
      'COVID sospechoso: fiebre + tos + anosmia (patognomónico)').
```

---

## 2. Inferencia

### `diagnostico/4`

```prolog
diagnostico(+ListaSintomas, -Diagnostico, -Severidad, -ReglasDisparadas)
```

Es el motor. Recibe los síntomas del usuario y devuelve el diagnóstico más probable, su severidad y todas las reglas que se dispararon para llegar a él.

Lo que hace por dentro, en orden:

1. Valida la entrada con `valida_entrada/1`.
2. Busca las reglas cuyas condiciones positivas están todas en los síntomas y cuyas condiciones negativas no está presente ninguna.
3. Calcula el peso total de cada una con `calcula_peso/3`.
4. Se queda con la de mayor peso (`max_peso/2`).
5. Determina la severidad con `determina_severidad/3`.
6. Recoge todas las reglas que apoyan al diagnóstico ganador, no solo la primera.
7. Si ninguna regla encaja con claridad, recurre a `hipotesis_parciales/2`.

Valores de salida:

- `Diagnostico`: `gripe`, `resfriado`, `covid`, `alergia`, `neumonia`, `indeterminado` o `desconocido`.
- `Severidad`: `alta`, `media_alta`, `media`, `baja` o `ninguna`.
- `ReglasDisparadas`: lista de IDs, por ejemplo `[r1_gripe, r2_gripe_completa]`.

### `consultar_diagnostico/4`

```prolog
consultar_diagnostico(+Sintomas, -Diagnostico, -Severidad, -Trace)
```

Envoltorio pensado para llamadas de Prolog a Prolog. Devuelve la traza como un término `trace/4` con estructuras nativas. Desde Python no conviene usarlo: ahí se usa `consultar_diagnostico_texto/4`, explicado abajo.

```prolog
trace(FiredRules, ProvenFacts, Discarded, ReglasIDs)
```

- `FiredRules`: `[regla(ID, CondPos, CondNeg, Desc), ...]`
- `ProvenFacts`: `[sintoma(Sintoma, Peso), ...]`
- `Discarded`: `[descartada(Diag, Razon, Compartidos), ...]`
- `ReglasIDs`: `[ID, ...]`

### `consultar_diagnostico_texto/4` (el que usa Python)

```prolog
consultar_diagnostico_texto(+Sintomas, -Diagnostico, -Severidad, -TraceTexto)
```

Hace lo mismo que `consultar_diagnostico/4`, pero entrega la traza serializada como texto con `term_to_atom/2`. Existe por una limitación concreta: con PySwip 0.3.x, los términos compuestos pierden los nombres de sus átomos al cruzar el puente. Pasándolos como texto, Python los reconstruye con `parse_prolog_term()` sin perder nada.

`TraceTexto` es un átomo con la representación textual del término `trace/4` completo.

---

## 3. Explicabilidad ("¿Por qué?")

### `trace_inferencia/5`

```prolog
trace_inferencia(+Diagnostico, +Sintomas, -FiredRules, -ProvenFacts, -DiscardedHypotheses)
```

Arma la traza de auditoría de un diagnóstico.

| Argumento             | Estructura                                 | Qué contiene                                                         |
| --------------------- | ------------------------------------------ | -------------------------------------------------------------------- |
| `FiredRules`          | `regla(ID, CondPos, CondNeg, Descripcion)` | Reglas que se activaron                                              |
| `ProvenFacts`         | `sintoma(Sintoma, Peso)`                   | Síntomas del usuario que respaldan el diagnóstico (peso mayor que 0) |
| `DiscardedHypotheses` | `descartada(Diag, Razon, Compartidos)`     | Alternativas que compartían síntomas pero se descartaron             |

Razones de descarte posibles:

- `falta_sintoma_clave(Clave)`: falta el síntoma patognomónico que la enfermedad exige.
- `sintoma_excluyente(Excluyente)`: hay un síntoma presente que excluye la enfermedad.
- `peso_insuficiente(PesoActual, Umbral)`: la evidencia total no llega al mínimo.
- `reglas_incompletas(Faltantes)`: faltan estos síntomas para completar la regla más cercana.
- `causa_desconocida`: ninguna de las anteriores explica el descarte.

### `hipotesis_descartadas/3`

```prolog
hipotesis_descartadas(+Sintomas, +DiagnosticoActual, -ListaDescartadas)
```

Busca las enfermedades que compartían síntomas con el caso pero que no ganaron, y devuelve una lista de `descartada(Diagnostico, Razon, SintomasCompartidos)`.

Se apoya en estos predicados:

- `comparte_sintomas/3`: intersección entre los síntomas del usuario y los de la enfermedad.
- `motivo_descarte/3`: decide cuál de las razones de arriba aplica.
- `regla_mas_cercana/3`: ver sección 5.
- `sintoma_clave/2`: síntomas patognomónicos por enfermedad.
- `sintoma_excluyente/2`: síntomas que descartan una enfermedad (por ejemplo, fiebre descarta alergia).
- `umbral_minimo/2`: peso mínimo que debe reunirse para considerar una enfermedad.

---

## 4. Recomendación ("¿Qué falta?")

### `recomendar_sintoma/4`

```prolog
recomendar_sintoma(+SintomasParciales, -SintomaRecomendado, -HipotesisCompetidoras, -Explicacion)
```

Es el predicado de desempate. Cuando los síntomas no alcanzan para decidir, elige qué preguntar a continuación para separar mejor las hipótesis que siguen en juego.

Algoritmo:

1. `hipotesis_parciales/2` encuentra las enfermedades con al menos un síntoma en común.
2. `competidoras/3` se queda con las que están a 3 puntos o menos del máximo.
3. `sintomas_no_preguntados/2` lista los síntomas que el usuario aún no ha indicado.
4. `mejor_discriminador/3` elige el síntoma que más separa a las competidoras.
5. `genera_explicacion_recomendacion/3` redacta el mensaje para el usuario.

Salidas:

- `SintomaRecomendado`: el síntoma a preguntar (`fiebre`, `perdida_olfato`, etc.).
- `HipotesisCompetidoras`: lista de `parcial(Diag, Peso, SintomasMatch)`.
- `Explicacion`: texto listo para mostrar.

### `consultar_recomendacion/4`

```prolog
consultar_recomendacion(+Sintomas, -SintomaRec, -Hipotesis, -Explicacion)
```

Envoltorio directo de `recomendar_sintoma/4` para uso entre predicados Prolog. Las hipótesis salen como términos nativos. Desde Python se usa la variante `_texto`.

### `consultar_recomendacion_texto/4` (el que usa Python)

```prolog
consultar_recomendacion_texto(+Sintomas, -SintomaRec, -HipotesisTexto, -Explicacion)
```

Igual que el anterior, pero con las hipótesis serializadas como texto, por la misma razón que en `consultar_diagnostico_texto/4`: PySwip 0.3.x pierde los nombres de los átomos en los términos compuestos. `HipotesisTexto` es un átomo con la lista `[parcial(Diag, Peso, SintomasMatch), ...]` escrita como texto, que Python parsea con `parse_prolog_term()`.

### `hipotesis_parciales/2`

```prolog
hipotesis_parciales(+Sintomas, -ListaParciales)
```

Encuentra toda enfermedad con al menos un síntoma en común con la entrada. Recorre `listar_todas_enfermedades/1`, lo que evita duplicados. Devuelve `parcial(Diagnostico, PesoTotal, SintomasQueMatch)`.

### `competidoras/3`

```prolog
competidoras(+Parciales, +Sintomas, -Competidoras)
```

Deja solo las hipótesis que siguen "en competencia". El criterio es `Peso >= MaxPeso - 3`.

### `mejor_discriminador/3`

```prolog
mejor_discriminador(+SintomasCandidatos, +HipotesisCompetidoras, -MejorSintoma)
```

Elige, entre los síntomas aún no preguntados, el que mejor separa a las competidoras. La métrica es:

```
poder_discriminativo = (MaxPeso - MinPeso) + sintoma_peso(Sintoma, Base)
```

### `poder_discriminativo/3`

```prolog
poder_discriminativo(+Sintoma, +Hipotesis, -Poder)
```

Calcula esa métrica para un síntoma concreto: la dispersión de sus pesos entre las hipótesis más su prioridad base.

### `genera_explicacion_recomendacion/3`

```prolog
genera_explicacion_recomendacion(+Sintoma, +Hipotesis, -Explicacion)
```

Redacta el mensaje que ve el usuario. Solo usa los nombres de los diagnósticos, extraídos de los términos `parcial/3`.

---

## 5. Auxiliares

### `valida_entrada/1`

```prolog
valida_entrada(+Lista)
```

Comprueba que la entrada sea una lista y que todos sus términos sean ground, es decir, sin variables libres.

### `subset/2`

```prolog
subset(+SubLista, +SuperLista)
```

Verdadero si todos los elementos de `SubLista` están en `SuperLista`.

### `calcula_peso/3` y `calcula_peso_total/3`

```prolog
calcula_peso(+Sintomas, +Enfermedad, -PesoTotal)
calcula_peso_total(+Sintomas, +Enfermedad, -PesoTotal)
```

Suman los pesos de los síntomas de la lista para una enfermedad. `calcula_peso_total/3` es un alias.

### `max_peso/2`

```prolog
max_peso(+ListaTuplas4, -TuplaMaxima)
```

Devuelve la tupla con mayor peso, que va en la cuarta posición. Las tuplas tienen la forma `(ReglaID, Diag, Desc, Peso)`.

### `max_peso_parcial/2`

```prolog
max_peso_parcial(+ListaParciales, -MaxPeso)
```

Peso máximo dentro de una lista de términos `parcial(Diag, Peso, Sintomas)`.

### `peso_ge/2`

```prolog
peso_ge(+Umbral, +Parcial)
```

Pensado como filtro para `include/3`: verdadero si el peso de un `parcial/3` es mayor o igual que el umbral.

### `sintomas_no_preguntados/2`

```prolog
sintomas_no_preguntados(+SintomasUsuario, -SintomasNoPreguntados)
```

Diferencia entre `all_sintomas_conocidos/1` y los síntomas que ya dio el usuario.

### `all_sintomas_conocidos/1` y `listar_todos_sintomas/1`

```prolog
all_sintomas_conocidos(-Lista)
listar_todos_sintomas(-Lista)
```

Ambos devuelven la lista canónica de los 10 síntomas del dominio. El segundo es el que consulta Python para poblar la interfaz.

### `listar_todas_enfermedades/1`

```prolog
listar_todas_enfermedades(-Lista)
```

Lista canónica de las 5 enfermedades del dominio.

### `determina_severidad/3`

```prolog
determina_severidad(+ReglaID, +Sintomas, -Severidad)
```

Clasifica la severidad según los síntomas de alarma presentes:

- `alta`: `dificultad_respirar` junto con `dolor_pecho`.
- `media_alta`: `fiebre` junto con `perdida_olfato`.
- `media`: `fiebre`.
- `baja`: cualquier otro caso.

### `regla_mas_cercana/3`

```prolog
regla_mas_cercana(+Enfermedad, +SintomasUsuario, -SintomasFaltantes)
```

De todas las reglas de una enfermedad, elige la que está más cerca de cumplirse, es decir, a la que le faltan menos síntomas positivos, y devuelve cuáles son. Alimenta la razón de descarte `reglas_incompletas`.

---

## 6. Qué usa Python

Nota: `main.py` solo llama a las variantes `_texto`, por el problema de PySwip 0.3.x descrito arriba. Las versiones sin `_texto` quedan para uso interno entre predicados Prolog.

| Predicado                       | Aridad | Quién lo usa       | Para qué                                        |
| ------------------------------- | ------ | ------------------ | ----------------------------------------------- |
| `consultar_diagnostico_texto`   | 4      | Python (principal) | Diagnóstico con la traza serializada como texto |
| `consultar_recomendacion_texto` | 4      | Python (principal) | Síntoma a preguntar y competidoras serializadas |
| `listar_todos_sintomas`         | 1      | Python (auxiliar)  | Poblar la lista de síntomas en la UI            |
| `listar_todas_enfermedades`     | 1      | Python (auxiliar)  | Información del dominio                         |
| `consultar_diagnostico`         | 4      | Prolog             | Diagnóstico con términos compuestos             |
| `consultar_recomendacion`       | 4      | Prolog             | Recomendación con términos compuestos           |
| `diagnostico`                   | 4      | Interno            | Motor de inferencia                             |
| `trace_inferencia`              | 5      | Interno            | Genera la traza de auditoría                    |
| `recomendar_sintoma`            | 4      | Interno            | Lógica de desempate                             |
| `hipotesis_descartadas`         | 3      | Interno            | Explicación de alternativas                     |

---

## 7. Estructuras de datos

```prolog
trace(FiredRules, ProvenFacts, Discarded, ReglasIDs)

regla(ID, CondicionesPositivas, CondicionesNegativas, Descripcion)   % dentro de trace
sintoma(NombreSintoma, PesoEvidencia)                                % dentro de trace
descartada(Diagnostico, RazonDescarte, [SintomaCompartido1, ...])    % dentro de trace

parcial(Diagnostico, PesoTotal, [SintomaMatch1, ...])                % en la recomendación
```

Razones de descarte, tal como aparecen en `descartada/3`:

```prolog
falta_sintoma_clave(SintomaFaltante)
sintoma_excluyente(SintomaPresente)
peso_insuficiente(PesoActual, UmbralMinimo)
reglas_incompletas([SintomaFaltante1, SintomaFaltante2, ...])
causa_desconocida
```

---

## 8. Cómo extender la base

### Agregar una enfermedad

1. Definir `sintoma_enfermedad/3` para cada uno de sus síntomas.
2. Escribir sus reglas con `regla/5`, con IDs únicos del estilo `rXX_nueva`.
3. Declarar su síntoma patognomónico con `sintoma_clave/2`.
4. Si tiene excluyentes, declararlos con `sintoma_excluyente/2`.
5. Fijar su `umbral_minimo/2`.
6. Si introduce síntomas nuevos, asignarles `sintoma_peso/2`.

### Agregar un síntoma

1. Añadirlo a `all_sintomas_conocidos/1`.
2. Definir `sintoma_enfermedad/3` para cada enfermedad a la que afecte.
3. Asignarle `sintoma_peso/2` para decidir cuándo se pregunta.
4. Actualizar `SymptomInput._generar_labels()` en `main.py` para que aparezca en la interfaz.
