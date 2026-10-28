# main.py
"""
Interfaz Gráfica para RespiraClaro - Sistema Experto Médico con Explicabilidad (Caja Blanca)
Integrante B: Ingeniero de Integración y Explicabilidad

Arquitectura Híbrida:
- Capa Imperativa (Python): Streamlit GUI, captura/limpieza entradas, presentación visual
- Capa Simbólica (Prolog): Toda la lógica de inferencia, encadenamiento, traza y recomendaciones

Uso:
    streamlit run main.py
"""

import streamlit as st
from pyswip import Prolog
from typing import List, Dict, Any, Optional, Tuple
import json
import re

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="RespiraClaro - Sistema Experto Médico",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# BRIDGE PySwip → Python: parser de términos Prolog serializados
# ============================================================

_TOKEN_RE = re.compile(r"[^\s,()\[\]']+")
_NUM_RE = re.compile(r"-?\d+(\.\d+)?$")

def parse_prolog_term(text: str) -> Any:
    """Convierte el texto de un término Prolog (term_to_atom/2) a estructuras Python.
    Compuestos -> {"functor": str, "args": [...]}, listas -> list, átomos -> str,
    números -> int/float."""
    pos = 0
    n = len(text)

    def skip_ws():
        nonlocal pos
        while pos < n and text[pos].isspace():
            pos += 1

    def parse_quoted() -> str:
        nonlocal pos
        pos += 1
        out = []
        while pos < n:
            ch = text[pos]
            if ch == "\\" and pos + 1 < n:
                nxt = text[pos + 1]
                out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
                pos += 2
            elif ch == "'":
                if pos + 1 < n and text[pos + 1] == "'":
                    out.append("'")
                    pos += 2
                else:
                    pos += 1
                    return "".join(out)
            else:
                out.append(ch)
                pos += 1
        raise ValueError("Átomo entre comillas sin cerrar")

    def parse_seq(close: str) -> List[Any]:
        nonlocal pos
        items = []
        skip_ws()
        if pos < n and text[pos] == close:
            pos += 1
            return items
        while True:
            items.append(parse())
            skip_ws()
            if pos < n and text[pos] == ",":
                pos += 1
                continue
            if pos < n and text[pos] == close:
                pos += 1
                return items
            raise ValueError(f"Se esperaba ',' o '{close}' en la posición {pos}")

    def parse() -> Any:
        nonlocal pos
        skip_ws()
        if pos >= n:
            raise ValueError("Fin inesperado del término")
        if text[pos] == "[":
            pos += 1
            return parse_seq("]")
        if text[pos] == "'":
            name = parse_quoted()
        else:
            m = _TOKEN_RE.match(text, pos)
            if not m:
                raise ValueError(f"Carácter inesperado en la posición {pos}")
            name = m.group(0)
            pos = m.end()
            if _NUM_RE.match(name):
                return float(name) if "." in name else int(name)
        if pos < n and text[pos] == "(":
            pos += 1
            return {"functor": name, "args": parse_seq(")")}
        return name

    result = parse()
    skip_ws()
    if pos != n:
        raise ValueError(f"Texto sobrante en la posición {pos}")
    return result

# ============================================================
# MOTOR PROLOG (PySwip Bridge)
# ============================================================
class PrologEngine:
    """Wrapper para PySwip que maneja la conexión y consultas a Prolog."""

    def __init__(self, kb_path: str = "base_conocimiento.pl"):
        self.prolog = Prolog()
        self.kb_path = kb_path
        self._cargar_base_conocimiento()

    def _cargar_base_conocimiento(self):
        """Carga el archivo .pl en el motor Prolog."""
        try:
            self.prolog.consult(self.kb_path)
        except Exception as e:
            st.error(f"Error cargando base de conocimiento: {e}")
            raise

    def _sanitize_input(self, term: str) -> str:
        """Sanitiza entrada para Prolog: minúsculas, sin espacios, átomos válidos."""
        return term.lower().replace(" ", "_").replace("-", "_")

    def _sanitize_list(self, items: List[str]) -> List[str]:
        """Sanitiza una lista de síntomas."""
        return [self._sanitize_input(item) for item in items]

    def _prolog_list(self, items: List[str]) -> str:
        """Convierte lista Python a sintaxis de lista Prolog."""
        sanitized = self._sanitize_list(items)
        return "[" + ",".join(sanitized) + "]"

    def consultar_diagnostico(self, sintomas: List[str]) -> Dict[str, Any]:
        """
        Consulta el diagnóstico principal dado una lista de síntomas.
        Retorna dict con: diagnostico, severidad, trace (reglas, hechos, descartadas).
        """
        pl_list = self._prolog_list(sintomas)
        query = f"consultar_diagnostico_texto({pl_list}, Diagnostico, Severidad, Trace)"

        try:
            results = list(self.prolog.query(query))
            if not results:
                return {
                    "diagnostico": "desconocido",
                    "severidad": "ninguna",
                    "trace": {"FiredRules": [], "ProvenFacts": [], "Discarded": [], "ReglasIDs": []},
                    "error": "No se obtuvo resultado de Prolog"
                }

            result = results[0]
            return self._parse_trace_result(result)
        except Exception as e:
            st.error(f"Error en consulta diagnóstico: {e}")
            return {"error": str(e)}

    def _parse_trace_result(self, result: Dict) -> Dict:
        """Interpreta la traza (texto Prolog) y la convierte a estructuras Python."""
        fired_rules, proven_facts, discarded, reglas_ids = [], [], [], []
        try:
            trace_data = parse_prolog_term(str(result.get("Trace", "")))
            if isinstance(trace_data, dict) and trace_data.get("functor") == "trace":
                args = trace_data.get("args", [])
                if len(args) >= 4:
                    fired_rules, proven_facts, discarded, reglas_ids = args[:4]
        except ValueError as e:
            st.error(f"No se pudo interpretar la traza de Prolog: {e}")
        return {
            "diagnostico": str(result.get("Diagnostico", "desconocido")),
            "severidad": str(result.get("Severidad", "ninguna")),
            "trace": {
                "FiredRules": fired_rules,
                "ProvenFacts": proven_facts,
                "Discarded": discarded,
                "ReglasIDs": reglas_ids,
            },
        }

    def consultar_recomendacion(self, sintomas: List[str]) -> Dict[str, Any]:
        """Consulta qué síntoma preguntar a continuación para desempatar."""
        pl_list = self._prolog_list(sintomas)
        query = f"consultar_recomendacion_texto({pl_list}, SintomaRec, Hipotesis, Explicacion)"

        try:
            results = list(self.prolog.query(query))
            if not results:
                return {"sintoma_recomendado": None, "hipotesis": [], "explicacion": ""}

            result = results[0]
            return {
                "sintoma_recomendado": str(result.get("SintomaRec", "")),
                "hipotesis": parse_prolog_term(str(result.get("Hipotesis", "[]"))),
                "explicacion": str(result.get("Explicacion", ""))
            }
        except Exception as e:
            st.error(f"Error en consulta recomendación: {e}")
            return {"error": str(e)}

    def listar_sintomas(self) -> List[str]:
        """Obtiene la lista de todos los síntomas conocidos."""
        try:
            results = list(self.prolog.query("listar_todos_sintomas(Lista)"))
            if results:
                lista = results[0].get("Lista", [])
                return [str(s) for s in lista]
        except:
            pass
        # Fallback hardcoded
        return ["fiebre", "tos", "dolor_garganta", "congestion", "dolor_cabeza",
                "fatiga", "perdida_olfato", "estornudos", "dolor_pecho", "dificultad_respirar"]

    def listar_enfermedades(self) -> List[str]:
        """Obtiene la lista de todas las enfermedades conocidas."""
        try:
            results = list(self.prolog.query("listar_todas_enfermedades(Lista)"))
            if results:
                lista = results[0].get("Lista", [])
                return [str(s) for s in lista]
        except:
            pass
        return ["gripe", "resfriado", "covid", "alergia", "neumonia"]


# ============================================================
# COMPONENTES DE UI
# ============================================================

class SymptomInput:
    """Componente para entrada de síntomas."""

    def __init__(self, engine: PrologEngine):
        self.engine = engine
        self.sintomas_disponibles = engine.listar_sintomas()
        self.labels = self._generar_labels()

    def _generar_labels(self) -> Dict[str, str]:
        """Genera labels amigables para síntomas."""
        mapeo = {
            "fiebre": "🌡️ Fiebre",
            "tos": "🤧 Tos",
            "dolor_garganta": "😷 Dolor de garganta",
            "congestion": "🤧 Congestión nasal",
            "dolor_cabeza": "🤕 Dolor de cabeza",
            "fatiga": "😴 Fatiga",
            "perdida_olfato": "👃 Pérdida de olfato/gusto",
            "estornudos": "🤧 Estornudos",
            "dolor_pecho": "💔 Dolor en el pecho",
            "dificultad_respirar": "🫁 Dificultad para respirar"
        }
        return {s: mapeo.get(s, s.replace("_", " ").title()) for s in self.sintomas_disponibles}

    def _clear_selection(self):
        """Callback para limpiar todos los checkboxes."""
        for s in self.sintomas_disponibles:
            st.session_state[f"sym_{s}"] = False

    def _add_symptom(self, symptom: str):
        """Callback para agregar un síntoma."""
        st.session_state[f"sym_{symptom}"] = True

    def render(self) -> List[str]:
        """Renderiza el selector de síntomas y retorna los seleccionados."""
        st.sidebar.header("📋 Síntomas del Paciente")

        # Checkboxes organizados en grupos
        st.sidebar.subheader("Sistémicos")
        sistemicos = ["fiebre", "fatiga", "dolor_cabeza"]
        seleccionados = []
        for s in sistemicos:
            if st.sidebar.checkbox(self.labels[s], key=f"sym_{s}"):
                seleccionados.append(s)

        st.sidebar.subheader("Respiratorios")
        respiratorios = ["tos", "dolor_garganta", "congestion", "estornudos",
                        "dolor_pecho", "dificultad_respirar"]
        for s in respiratorios:
            if st.sidebar.checkbox(self.labels[s], key=f"sym_{s}"):
                seleccionados.append(s)

        st.sidebar.subheader("Específicos")
        especificos = ["perdida_olfato"]
        for s in especificos:
            if st.sidebar.checkbox(self.labels[s], key=f"sym_{s}"):
                seleccionados.append(s)

        # Botón para limpiar - usa callback para desmarcar checkboxes
        if st.sidebar.button("🗑️ Limpiar selección", use_container_width=True, on_click=self._clear_selection):
            pass  # on_click maneja la limpieza

        return seleccionados


class DiagnosisDisplay:
    """Componente para mostrar el diagnóstico y severidad."""

    SEVERITY_COLORS = {
        "alta": "🔴",
        "media_alta": "🟠",
        "media": "🟡",
        "baja": "🟢",
        "ninguna": "⚪"
    }

    SEVERITY_LABELS = {
        "alta": "Alta - Requiere atención médica urgente",
        "media_alta": "Media-Alta - Consulta médica recomendada",
        "media": "Media - Seguimiento médico",
        "baja": "Baja - Autocuidado y observación",
        "ninguna": "Sin diagnóstico"
    }

    DIAGNOSIS_LABELS = {
        "gripe": "🤒 Gripe (Influenza)",
        "resfriado": "🤧 Resfriado Común",
        "covid": "🦠 COVID-19",
        "alergia": "🌸 Alergia/Rinitis Alérgica",
        "neumonia": "🫁 Neumonía",
        "indeterminado": "❓ Indeterminado (evidencia insuficiente)",
        "desconocido": "❓ Desconocido",
        "none": "❓ Sin diagnóstico"
    }

    def render(self, resultado: Dict):
        """Renderiza el panel de diagnóstico principal."""
        diag = resultado.get("diagnostico", "desconocido")
        sev = resultado.get("severidad", "ninguna")

        col1, col2 = st.columns([2, 1])

        with col1:
            label = self.DIAGNOSIS_LABELS.get(diag, diag.title())
            st.markdown(f"## {label}")

            if "error" in resultado:
                st.error(f"Error: {resultado['error']}")

        with col2:
            icon = self.SEVERITY_COLORS.get(sev, "⚪")
            label_sev = self.SEVERITY_LABELS.get(sev, sev)
            st.markdown(f"### {icon} Severidad: {label_sev}")

            # Progress bar visual para severidad
            sev_values = {"alta": 1.0, "media_alta": 0.75, "media": 0.5, "baja": 0.25, "ninguna": 0}
            st.progress(sev_values.get(sev, 0))

        st.divider()


class ExplainabilityPanel:
    """Panel de Explicabilidad: '¿Por qué?' - Traza de inferencia completa."""

    def render(self, trace: Dict):
        """Renderiza la traza completa de inferencia."""
        st.header("🔍 Auditoría de Inferencia - ¿Por qué este diagnóstico?")

        if not trace or not any(trace.values()):
            st.info("No hay traza disponible para este diagnóstico.")
            return

        # 1. Reglas Disparadas
        st.subheader("⚡ Reglas Disparadas")
        fired_rules = trace.get("FiredRules", [])
        if fired_rules:
            for i, rule in enumerate(fired_rules, 1):
                if isinstance(rule, dict):
                    functor = rule.get("functor", "")
                    args = rule.get("args", [])
                    # Nueva estructura: regla(ID, CondicionesPos, CondicionesNeg, Desc)
                    if functor == "regla" and len(args) >= 4:
                        rule_id = args[0]
                        conds_pos = args[1] if len(args) > 1 else []
                        conds_neg = args[2] if len(args) > 2 else []
                        desc = args[3] if len(args) > 3 else ""
                        with st.expander(f"Regla {i}: {rule_id}"):
                            st.write(f"**Descripción:** {desc}")
                            if conds_pos:
                                st.write(f"**Condiciones positivas:** {', '.join(str(c) for c in conds_pos)}")
                            if conds_neg:
                                st.write(f"**Condiciones negativas (excluyentes):** {', '.join(str(c) for c in conds_neg)}")
                    else:
                        st.write(f"Regla {i}: {rule}")
                else:
                    st.write(f"Regla {i}: {rule}")
        else:
            st.write("*Ninguna regla se disparó completamente*")

        # 2. Hechos Comprobados
        st.subheader("✅ Hechos Comprobados (Evidencia Validada)")
        proven_facts = trace.get("ProvenFacts", [])
        if proven_facts:
            cols = st.columns(3)
            for i, fact in enumerate(proven_facts):
                with cols[i % 3]:
                    if isinstance(fact, dict) and fact.get("functor") == "sintoma":
                        args = fact.get("args", [])
                        if len(args) >= 2:
                            sintoma = args[0]
                            peso = args[1]
                            st.metric(label=sintoma.replace("_", " ").title(), value=f"Peso: {peso}")
                    else:
                        st.write(f"• {fact}")
        else:
            st.write("*No hay síntomas que apoyen directamente este diagnóstico*")

        # 3. Hipótesis Descartadas
        st.subheader("❌ Hipótesis Alternativas Descartadas")
        discarded = trace.get("Discarded", [])
        if discarded:
            for hyp in discarded:
                if isinstance(hyp, dict) and hyp.get("functor") == "descartada":
                    args = hyp.get("args", [])
                    if len(args) >= 3:
                        diag = args[0]
                        razon = args[1]
                        compartidos = args[2]
                        with st.expander(f"❌ {diag.title()} - {self._format_razon(razon)}"):
                            st.write(f"**Síntomas compartidos:** {', '.join(str(c).replace('_', ' ') for c in compartidos)}")
                            st.write(f"**Motivo de descarte:** {self._format_razon_detallado(razon)}")
                    else:
                        st.write(f"• {hyp}")
                else:
                    st.write(f"• {hyp}")
        else:
            st.write("*No hay hipótesis alternativas con síntomas compartidos*")

    def _format_razon(self, razon) -> str:
        """Formatea la razón de descarte para mostrar en el expander."""
        if isinstance(razon, dict):
            functor = razon.get("functor", "")
            args = razon.get("args", [])
            if functor == "falta_sintoma_clave":
                return f"Falta síntoma clave: {args[0] if args else '?'}"
            elif functor == "sintoma_excluyente":
                return f"Síntoma excluyente: {args[0] if args else '?'}"
            elif functor == "peso_insuficiente":
                return "Peso insuficiente ({}/{})".format(args[0] if args else "?", args[1] if len(args)>1 else "?")
            elif functor == "reglas_incompletas":
                faltantes = args[0] if args and isinstance(args[0], list) else []
                return "Reglas incompletas: faltan {}".format(", ".join(faltantes) or "?")
        return str(razon)

    def _format_razon_detallado(self, razon) -> str:
        """Formatea la razón detallada."""
        if isinstance(razon, dict):
            functor = razon.get("functor", "")
            args = razon.get("args", [])
            if functor == "falta_sintoma_clave":
                return "El diagnóstico requiere el síntoma patognomónico **{}** que no está presente.".format(args[0].replace('_', ' ') if args else '?')
            elif functor == "sintoma_excluyente":
                return "La presencia de **{}** excluye este diagnóstico.".format(args[0].replace('_', ' ') if args else '?')
            elif functor == "peso_insuficiente":
                return "Peso de evidencia **{}** por debajo del umbral mínimo **{}**.".format(args[0] if args else '?', args[1] if len(args)>1 else '?')
            elif functor == "reglas_incompletas":
                faltantes = args[0] if args and isinstance(args[0], list) else []
                nombres = ", ".join(a.replace('_', ' ') for a in faltantes) or "?"
                return "Las reglas de este diagnóstico están incompletas. Faltan: **{}**.".format(nombres)
        return str(razon)


class RecommendationPanel:
    """Panel de Recomendación: '¿Qué falta?' - Sugerencia de siguiente pregunta."""

    def __init__(self):
        # Se inicializa vacío, el callback se configura en render
        pass

    def _add_symptom_callback(self, symptom: str):
        """Callback para agregar un síntoma recomendado."""
        st.session_state[f"sym_{symptom}"] = True

    def render(self, recomendacion: Dict, sintomas_actuales: List[str]):
        """Renderiza el panel de recomendación cuando hay evidencia insuficiente."""
        st.header("🎯 Recomendación - ¿Qué falta para confirmar?")

        if "error" in recomendacion:
            st.error(f"Error: {recomendacion['error']}")
            return

        sintoma_rec = recomendacion.get("sintoma_recomendado")
        hipotesis = recomendacion.get("hipotesis", [])
        explicacion = recomendacion.get("explicacion", "")

        if not sintoma_rec or sintoma_rec in ["", "none", "null"]:
            st.success("✅ Evidencia suficiente para diagnóstico definitivo. No se requieren más preguntas.")
            return

        # Tarjeta principal de recomendación
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            color: white;
            margin: 1rem 0;
        ">
            <h3>🎯 Próximo síntoma a investigar</h3>
            <h2>{sintoma_rec.replace('_', ' ').title()}</h2>
            <p>{explicacion}</p>
        </div>
        """, unsafe_allow_html=True)

        # Hipótesis en competencia
        if hipotesis:
            st.subheader("⚔️ Hipótesis en Competencia")
            for h in hipotesis:
                if isinstance(h, dict) and h.get("functor") == "parcial":
                    args = h.get("args", [])
                    if len(args) >= 3:
                        diag = args[0]
                        peso = args[1]
                        sintomas_match = args[2]
                        st.write(f"• **{diag.title()}** (peso: {peso}) - Síntomas: {', '.join(str(s).replace('_', ' ') for s in sintomas_match)}")

        # Botón rápido para agregar el síntoma recomendado - usa on_click
        if st.button(f"➕ Agregar '{sintoma_rec.replace('_', ' ')}' a síntomas",
                     use_container_width=True,
                     on_click=self._add_symptom_callback,
                     args=(sintoma_rec,)):
            pass  # on_click maneja la actualización


class TraceVisualizer:
    """Visualizador avanzado de traza (árbol/lista)."""

    def render_tree(self, trace: Dict, diagnostico: str = "Diagnóstico"):
        """Renderiza vista de árbol de la inferencia."""
        st.subheader("🌳 Vista de Árbol de Inferencia")

        # Usar graphviz en lugar de mermaid (más confiable en Streamlit)
        try:
            import graphviz
            dot = self._build_graphviz(trace, diagnostico)
            st.graphviz_chart(dot)
        except ImportError:
            # Fallback: mostrar como texto estructurado
            st.warning("📦 graphviz no instalado. Mostrando vista textual.")
            self._render_text_tree(trace, diagnostico)

    def _build_graphviz(self, trace: Dict, diagnostico: str) -> 'graphviz.Digraph':
        """Construye diagrama Graphviz de la inferencia."""
        import graphviz
        dot = graphviz.Digraph(comment='Inferencia', format='png')
        dot.attr(rankdir='TB', fontsize='12')
        dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')

        # Nodo raíz: diagnóstico
        dot.node('D', diagnostico, fillcolor='#e8f5e9', color='#2e7d32', fontcolor='#1b5e20')

        # Reglas disparadas
        for i, rule in enumerate(trace.get("FiredRules", []), 1):
            rule_id = f"R{i}"
            if isinstance(rule, dict):
                args = rule.get("args", [])
                # regla(ID, CondicionesPos, CondicionesNeg, Desc)
                label = args[3] if len(args) > 3 else str(rule)
                rule_label = f"{args[0]}\\n{label}" if len(args) > 0 else label
            else:
                rule_label = str(rule)
            dot.node(rule_id, rule_label, fillcolor='#e3f2fd', color='#1565c0', fontcolor='#0d47a1')
            dot.edge(rule_id, 'D')

        # Hechos
        for i, fact in enumerate(trace.get("ProvenFacts", []), 1):
            fact_id = f"F{i}"
            if isinstance(fact, dict) and fact.get("functor") == "sintoma":
                args = fact.get("args", [])
                label = f"{args[0]} (peso: {args[1]})" if len(args) >= 2 else str(fact)
            else:
                label = str(fact)
            dot.node(fact_id, label, fillcolor='#fff3e0', color='#ef6c00', fontcolor='#e65100')
            dot.edge(fact_id, 'D')

        return dot

    def _render_text_tree(self, trace: Dict, diagnostico: str):
        """Renderiza vista textual como fallback."""
        st.write(f"**Diagnóstico:** {diagnostico}")
        st.write("")

        st.write("**Reglas disparadas:**")
        for i, rule in enumerate(trace.get("FiredRules", []), 1):
            if isinstance(rule, dict):
                args = rule.get("args", [])
                label = args[3] if len(args) > 3 else str(rule)
                rule_id = args[0] if len(args) > 0 else f"R{i}"
                st.write(f"  {i}. {rule_id}: {label}")
                if len(args) > 1 and args[1]:
                    st.write(f"     ✓ Condiciones: {', '.join(str(c) for c in args[1])}")
                if len(args) > 2 and args[2]:
                    st.write(f"     ✗ Excluyentes: {', '.join(str(c) for c in args[2])}")
            else:
                st.write(f"  {i}. {rule}")

        st.write("")
        st.write("**Hechos comprobados:**")
        for fact in trace.get("ProvenFacts", []):
            if isinstance(fact, dict) and fact.get("functor") == "sintoma":
                args = fact.get("args", [])
                if len(args) >= 2:
                    st.write(f"  • {args[0].replace('_', ' ').title()} (peso: {args[1]})")
                else:
                    st.write(f"  • {fact}")
            else:
                st.write(f"  • {fact}")


# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

def main():
    # Inicializar motor Prolog (cached)
    if "prolog_engine" not in st.session_state:
        try:
            st.session_state.prolog_engine = PrologEngine("base_conocimiento.pl")
        except Exception as e:
            st.error(f"""
            ❌ **Error inicializando Prolog**

            Asegúrate de tener:
            1. SWI-Prolog instalado y en PATH
            2. PySwip instalado: `pip install pyswip`
            3. El archivo `base_conocimiento.pl` en el mismo directorio

            Error: {e}
            """)
            st.stop()

    engine = st.session_state.prolog_engine

    # Componentes UI
    symptom_input = SymptomInput(engine)
    diagnosis_display = DiagnosisDisplay()
    explainability_panel = ExplainabilityPanel()
    recommendation_panel = RecommendationPanel()
    trace_viz = TraceVisualizer()

    # Título principal
    st.title("🏥 RespiraClaro: Sistema Experto Médico Auditable (Caja Blanca)")
    st.caption("Arquitectura Híbrida: Python (GUI) + Prolog (Motor Simbólico) | PySwip Bridge")

    # Sidebar: Entrada de síntomas
    sintomas_seleccionados = symptom_input.render()

    # Área principal
    if sintomas_seleccionados:
        # Consultar diagnóstico
        with st.spinner("🔄 Inferiendo diagnóstico..."):
            resultado = engine.consultar_diagnostico(sintomas_seleccionados)

        # Mostrar diagnóstico
        diagnosis_display.render(resultado)

        # Tabs para explicabilidad y recomendación
        tab1, tab2, tab3 = st.tabs(["🔍 ¿Por qué? (Explicabilidad)", "🎯 ¿Qué falta? (Recomendación)", "🌳 Vista Árbol"])

        with tab1:
            explainability_panel.render(resultado.get("trace", {}))

        with tab2:
            # Solo mostrar recomendación si diagnóstico es indeterminado o hay dudas
            diag = resultado.get("diagnostico", "")
            if diag in ["indeterminado", "desconocido", "none"] or resultado.get("severidad") in ["baja", "ninguna"]:
                with st.spinner("🔄 Calculando recomendación..."):
                    recomendacion = engine.consultar_recomendacion(sintomas_seleccionados)
                recommendation_panel.render(recomendacion, sintomas_seleccionados)
            else:
                st.success("✅ Diagnóstico con evidencia suficiente. No se requiere recomendación adicional.")
                if st.button("Ver recomendación igualmente"):
                    with st.spinner("🔄 Calculando recomendación..."):
                        recomendacion = engine.consultar_recomendacion(sintomas_seleccionados)
                    recommendation_panel.render(recomendacion, sintomas_seleccionados)

        with tab3:
            trace_viz.render_tree(resultado.get("trace", {}), resultado.get("diagnostico", "Diagnóstico"))

    else:
        # Estado inicial sin síntomas
        st.info("👈 Selecciona síntomas en el panel lateral para comenzar el diagnóstico.")

        # Mostrar información del sistema
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🦠 Enfermedades en la base de conocimiento")
            for enf in engine.listar_enfermedades():
                st.write(f"• {enf.title()}")

        with col2:
            st.subheader("📝 Síntomas disponibles")
            for s in engine.listar_sintomas():
                st.write(f"• {s.replace('_', ' ').title()}")

        st.divider()
        st.subheader("📖 Casos de Prueba Sugeridos")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Caso 1 - Inferencia Completa (Gripe):**
            - ✅ Fiebre
            - ✅ Tos
            - ✅ Dolor de cabeza
            - ✅ Fatiga
            - ✅ Dolor de garganta
            - ✅ Congestión

            *Resultado esperado: Gripe con traza completa*
            """)

        with col2:
            st.markdown("""
            **Caso 2 - Datos Insuficientes (Recomendación):**
            - ✅ Tos
            - ✅ Congestión

            *Resultado esperado: Indeterminado (ninguna regla completa) → Recomienda: "¿Tiene fiebre?"*
            """)

if __name__ == "__main__":
    main()


