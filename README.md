# RespiraClaro

Un sistema experto médico de caja blanca: cada diagnóstico que da se puede explicar paso a paso, y cuando no tiene datos suficientes te dice qué síntoma preguntar a continuación. Es el Entregable 2 de Sistemas Expertos (puente Python-PySwip y motor de explicabilidad).

La idea central es separar el razonamiento de la interfaz. Prolog se encarga de pensar (reglas, encadenamiento, traza, recomendaciones) y Python se encarga de todo lo demás (pantalla, entrada del usuario, presentación). Ninguna decisión médica vive en el código Python: si quieres cambiar cómo se diagnostica algo, tocas el `.pl`.

## Cómo está armado

```
Python (Streamlit + PySwip)
  - captura los síntomas
  - consulta a Prolog y parsea las respuestas
  - dibuja las pestañas "¿Por qué?" y "¿Qué falta?"
          |
          |  PySwip (Prolog embebido)
          v
Prolog (SWI-Prolog)
  - base de conocimiento
  - motor de inferencia con traza
  - módulo de recomendación (desempate entre hipótesis)
```

| Capa       | Qué hace                                                  | Con qué            |
| ---------- | --------------------------------------------------------- | ------------------ |
| Imperativa | GUI, limpieza de la entrada, presentación                 | Python y Streamlit |
| Simbólica  | Inferencia, traza, hipótesis descartadas, recomendaciones | SWI-Prolog         |

## Archivos

```
respira-claro/
├── base_conocimiento.pl      # Reglas y hechos del dominio (Prolog)
├── main.py                   # Interfaz Streamlit y puente PySwip
├── requirements.txt
├── PREDICATE_DICTIONARY.md   # Predicados Prolog con sus modos (+,-,?)
└── README.md
```

## Para correrlo

Necesitas Python 3.8 o superior y SWI-Prolog instalado, porque PySwip depende de él.

- Windows: instalador desde swi-prolog.org/download/stable y agregarlo al PATH.
- Linux: `sudo apt-get install swi-prolog`
- macOS: `brew install swi-prolog`

Comprueba que `swipl --version` responde en la terminal antes de seguir. La mayoría de los problemas de instalación se resuelven ahí.

```bash
cd respira-claro

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
streamlit run main.py
```

Se abre solo en `http://localhost:8501`.

## Qué esperar al usarlo

### Cuando hay evidencia suficiente: "¿Por qué?"

Marca en el panel lateral fiebre, tos, dolor de cabeza, fatiga, dolor de garganta y congestión. El sistema diagnostica gripe con severidad media. En la pestaña "¿Por qué?" ves el razonamiento completo:

- Reglas disparadas: `r1_gripe` y `r2_gripe_completa`.
- Hechos comprobados, cada uno con su peso (fiebre, tos, dolor de cabeza y fatiga pesan 3).
- Hipótesis descartadas y el motivo de cada descarte: COVID porque falta la pérdida de olfato, neumonía porque faltan dolor de pecho y disnea, alergia porque hay fiebre, resfriado porque sus reglas quedan incompletas (faltan estornudos).

### Cuando falta información: "¿Qué falta?"

Marca solo tos y congestión. Ninguna regla completa se dispara, así que el diagnóstico queda como indeterminado y las cinco enfermedades siguen compitiendo. En la pestaña "¿Qué falta?" el sistema recomienda preguntar por la fiebre, porque es el síntoma que mejor separa las hipótesis (por ejemplo, la alergia lo excluye y la gripe lo exige). Si pulsas el botón para agregarlo, la evaluación se repite sola con el nuevo dato.

## Lo que sabe el sistema

| Código      | Enfermedad       | Qué la caracteriza                              |
| ----------- | ---------------- | ----------------------------------------------- |
| `gripe`     | Influenza        | Fiebre, tos, cefalea y fatiga                   |
| `resfriado` | Resfriado común  | Congestión, estornudos y dolor de garganta      |
| `covid`     | COVID-19         | Pérdida de olfato (patognomónico), fiebre y tos |
| `alergia`   | Rinitis alérgica | Estornudos y congestión, sin fiebre             |
| `neumonia`  | Neumonía         | Fiebre, tos, dolor de pecho y disnea            |

Los diez síntomas: `fiebre`, `tos`, `dolor_garganta`, `congestion`, `dolor_cabeza`, `fatiga`, `perdida_olfato`, `estornudos`, `dolor_pecho`, `dificultad_respirar`.

## Extenderlo

### Agregar una enfermedad

En `base_conocimiento.pl`:

```prolog
% Qué síntomas la componen y cuánto pesan
sintoma_enfermedad(nuevo_sintoma, nueva_enfermedad, Peso).

% Regla de diagnóstico: positivos, excluyentes, enfermedad, descripción
regla(rXX_nueva, [sintoma1, sintoma2], [], nueva_enfermedad, 'Descripción').
% Con excluyentes:
regla(rXX_nueva, [sintoma1], [excluyente1], nueva_enfermedad, 'Descripción').

% Síntoma clave, excluyentes y umbral
sintoma_clave(nueva_enfermedad, sintoma_patognomonico).
sintoma_excluyente(nueva_enfermedad, sintoma_excluyente).  % si aplica
umbral_minimo(nueva_enfermedad, Umbral).
```

Después, en `main.py`, agrega las etiquetas nuevas en `SymptomInput._generar_labels()` para que aparezcan en la interfaz.

### Cambiar el orden en que se pregunta

Edita `sintoma_peso/2` en `base_conocimiento.pl`. Un peso mayor hace que el síntoma se sugiera antes.

## Si algo falla

| Error                                           | Qué revisar                                                       |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'pyswip'` | `pip install pyswip` y confirmar que SWI-Prolog está en el PATH   |
| `PrologLaunchError` o `File not found`          | Reinstalar SWI-Prolog, reiniciar la terminal y probar `swipl`     |
| `SyntaxError` al cargar el `.pl`                | Buscar comas, puntos finales o paréntesis sin cerrar              |
| Variables libres en una consulta                | Validar la entrada en Python y usar `ground/1` antes de consultar |

## Más documentación

El detalle de cada predicado (modos y descripción) está en [PREDICATE_DICTIONARY.md](PREDICATE_DICTIONARY.md).

Proyecto académico, Entregable 2 de Sistemas Expertos.
