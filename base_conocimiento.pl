% base_conocimiento.pl
% Base de Conocimiento para RespiraClaro - Sistema Experto Médico con Explicabilidad
% Autor: Integrante A (Ingeniero del Conocimiento y Motor Simbólico)
% Fecha: 2026
%
% Dominio: Diagnóstico diferencial de enfermedades respiratorias
% Enfermedades: gripe, resfriado, covid, alergia, neumonía
% Síntomas: fiebre, tos, dolor_garganta, congestión, dolor_cabeza,
%           fatiga, perdida_olfato, estornudos, dolor_pecho, dificultad_respirar

% ============================================================
% HECHOS BASE: Síntomas conocidos por enfermedad
% ============================================================

% sintoma_enfermedad(+Sintoma, +Enfermedad, +Peso)
% Peso: 1=bajo, 2=medio, 3=alto, 4=muy alto (patognomónico)
sintoma_enfermedad(fiebre, gripe, 3).
sintoma_enfermedad(tos, gripe, 3).
sintoma_enfermedad(dolor_garganta, gripe, 2).
sintoma_enfermedad(congestion, gripe, 2).
sintoma_enfermedad(dolor_cabeza, gripe, 3).
sintoma_enfermedad(fatiga, gripe, 3).
sintoma_enfermedad(perdida_olfato, gripe, 1).

sintoma_enfermedad(fiebre, resfriado, 1).
sintoma_enfermedad(tos, resfriado, 3).
sintoma_enfermedad(dolor_garganta, resfriado, 3).
sintoma_enfermedad(congestion, resfriado, 4).
sintoma_enfermedad(estornudos, resfriado, 4).
sintoma_enfermedad(dolor_cabeza, resfriado, 1).
sintoma_enfermedad(fatiga, resfriado, 1).

sintoma_enfermedad(fiebre, covid, 3).
sintoma_enfermedad(tos, covid, 4).
sintoma_enfermedad(dolor_garganta, covid, 2).
sintoma_enfermedad(congestion, covid, 1).
sintoma_enfermedad(dolor_cabeza, covid, 2).
sintoma_enfermedad(fatiga, covid, 3).
sintoma_enfermedad(perdida_olfato, covid, 4).
sintoma_enfermedad(dificultad_respirar, covid, 3).

sintoma_enfermedad(congestion, alergia, 3).
sintoma_enfermedad(estornudos, alergia, 4).
sintoma_enfermedad(dolor_garganta, alergia, 1).
sintoma_enfermedad(perdida_olfato, alergia, 1).
sintoma_enfermedad(fiebre, alergia, 0).  % Excluyente: alergia no da fiebre
sintoma_enfermedad(tos, alergia, 1).

sintoma_enfermedad(fiebre, neumonia, 4).
sintoma_enfermedad(tos, neumonia, 4).
sintoma_enfermedad(dolor_pecho, neumonia, 4).
sintoma_enfermedad(dificultad_respirar, neumonia, 4).
sintoma_enfermedad(fatiga, neumonia, 3).
sintoma_enfermedad(dolor_cabeza, neumonia, 1).

% ============================================================
% PESOS DE SÍNTOMAS PARA RECOMENDACIÓN (desempate)
% ============================================================

% sintoma_peso(+Sintoma, -Peso)
% Prioridad global del síntoma para preguntas de desempate
sintoma_peso(fiebre, 10).              % Clave para diferenciar alergia (excluyente) vs resto
sintoma_peso(perdida_olfato, 9).       % Muy específico (COVID)
sintoma_peso(dificultad_respirar, 8).  % Grave, específico (neumonía/COVID grave)
sintoma_peso(dolor_pecho, 7).          % Específico (neumonía)
sintoma_peso(tos, 6).                  % Común
sintoma_peso(congestion, 5).           % Común
sintoma_peso(dolor_garganta, 4).
sintoma_peso(estornudos, 3).           % Específico (alergia/resfriado)
sintoma_peso(dolor_cabeza, 3).
sintoma_peso(fatiga, 2).               % Muy inespecífico

% ============================================================
% REGLAS DE DIAGNÓSTICO CON TRAZA
% ============================================================

% regla(+ReglaID, +CondicionesPositivas, +CondicionesNegativas, +Conclusión, +Descripción)
regla(r1_gripe, [fiebre, tos, dolor_cabeza, fatiga], [], gripe,
      'Cuadro clásico gripal: fiebre + tos + cefalea + fatiga').
regla(r2_gripe_completa, [fiebre, tos, dolor_garganta, congestion, dolor_cabeza, fatiga], [], gripe,
      'Gripe con síntomas respiratorios superiores completos').

regla(r3_resfriado, [tos, dolor_garganta, congestion, estornudos], [], resfriado,
      'Resfriado común: congestión + estornudos + dolor garganta + tos').
regla(r4_resfriado_leve, [congestion, estornudos, dolor_garganta], [], resfriado,
      'Resfriado leve: triada nasal/faríngea').

regla(r5_covid, [fiebre, tos, perdida_olfato], [], covid,
      'COVID sospechoso: fiebre + tos + anosmia (patognomónico)').
regla(r6_covid_completo, [fiebre, tos, perdida_olfato, fatiga, dolor_cabeza], [], covid,
      'COVID confirmado: cuadro completo con anosmia').
regla(r7_covid_grave, [fiebre, tos, dificultad_respirar, fatiga], [], covid,
      'COVID grave: disnea + fiebre + tos').

regla(r8_alergia, [congestion, estornudos], [fiebre], alergia,
      'Rinitis alérgica: congestión + estornudos + SIN fiebre').
regla(r9_alergia_leve, [estornudos, congestion], [fiebre, tos], alergia,
      'Alergia leve: solo síntomas nasales sin sistémicos').

regla(r10_neumonia, [fiebre, tos, dolor_pecho, dificultad_respirar], [], neumonia,
      'Neumonía: fiebre + tos productiva + dolor pleurítico + disnea').
regla(r11_neumonia_grave, [fiebre, tos, dolor_pecho, dificultad_respirar, fatiga], [], neumonia,
      'Neumonía grave: cuadro completo con fatiga marcada').

% ============================================================
% PREDICADOS PRINCIPALES DE INFERENCIA
% ============================================================

% diagnostico(+ListaSintomas, -Diagnostico, -Severidad, -ReglasDisparadas)
% Infiere el diagnóstico principal dado una lista de síntomas presentes
diagnostico(Sintomas, Diagnostico, Severidad, ReglasDisparadas) :-
    % Validar entrada
    valida_entrada(Sintomas),
    % Buscar todas las reglas que coincidan (condiciones positivas incluidas Y negativas ausentes)
    findall((ReglaID, Diag, Desc, PesoTotal),
            (regla(ReglaID, CondicionesPos, CondicionesNeg, Diag, Desc),
             subset(CondicionesPos, Sintomas),
             % Verificar que NINGUNA condición negativa está presente
             \+ (member(Neg, CondicionesNeg), member(Neg, Sintomas)),
             calcula_peso(CondicionesPos, Diag, PesoTotal)),
            Candidatas),
    % Seleccionar la de mayor peso
    (Candidatas \= [] ->
        max_peso(Candidatas, (MejorRegla, MejorDiag, _, _)),
        determina_severidad(MejorRegla, Sintomas, Severidad),
        Diagnostico = MejorDiag,
        % Devolver TODAS las reglas que dispararon (no solo la mejor)
        findall(ReglaID,
                (member((ReglaID, Diag, _, _), Candidatas), Diag = MejorDiag),
                ReglasDisparadas)
    ;   % Sin diagnóstico claro -> ver hipótesis parciales
        hipotesis_parciales(Sintomas, Parciales),
        (Parciales \= [] ->
            ReglasDisparadas = Parciales,
            Diagnostico = indeterminado,
            Severidad = baja
        ;   Diagnostico = desconocido,
            Severidad = ninguna,
            ReglasDisparadas = []
        )
    ).

% ============================================================
% MÓDULO DE EXPLICABILIDAD ("¿Por qué?")
% ============================================================

% trace_inferencia(+Diagnostico, +Sintomas, -FiredRules, -ProvenFacts, -DiscardedHypotheses)
% Devuelve la traza completa de inferencia para un diagnóstico
trace_inferencia(Diagnostico, Sintomas, FiredRules, ProvenFacts, DiscardedHypotheses) :-
    diagnostico(Sintomas, Diagnostico, _, ReglasIDs),
    % Reglas que se dispararon exitosamente
    findall(regla(ID, CondicionesPos, CondicionesNeg, Desc),
            (member(ID, ReglasIDs), regla(ID, CondicionesPos, CondicionesNeg, Diagnostico, Desc)),
            FiredRules),
    % Hechos comprobados (síntomas que unificaron)
    findall(sintoma(S, Peso),
            (member(S, Sintomas), sintoma_enfermedad(S, Diagnostico, Peso), Peso > 0),
            ProvenFacts),
    % Hipótesis alternativas descartadas
    hipotesis_descartadas(Sintomas, Diagnostico, DiscardedHypotheses).

% hipotesis_descartadas(+Sintomas, +DiagnosticoActual, -ListaDescartadas)
% Encuentra diagnósticos que compartían síntomas pero fueron descartados
hipotesis_descartadas(Sintomas, DiagnosticoActual, Descartadas) :-
    listar_todas_enfermedades(Todas),
    findall(descartada(Diag, Razon, SintomasCompartidos),
            (member(Diag, Todas),
             Diag \= DiagnosticoActual,
             Diag \= indeterminado,
             Diag \= desconocido,
             Diag \= none,
             comparte_sintomas(Sintomas, Diag, SintomasCompartidos),
             SintomasCompartidos \= [],
             motivo_descarte(Sintomas, Diag, Razon)),
            Descartadas).

% comparte_sintomas(+SintomasUsuario, +Enfermedad, -SintomasCompartidos)
comparte_sintomas(Sintomas, Enfermedad, Compartidos) :-
    findall(S, (member(S, Sintomas), sintoma_enfermedad(S, Enfermedad, Peso), Peso > 0), Compartidos).

% motivo_descarte(+Sintomas, +Enfermedad, -Razon)
motivo_descarte(Sintomas, Enfermedad, Razon) :-
    (   % Tiene síntoma excluyente (PRIORITARIO)
        sintoma_excluyente(Enfermedad, Excluyente),
        member(Excluyente, Sintomas)
    ->  Razon = sintoma_excluyente(Excluyente)
    ;   % Falta síntoma clave patognomónico
        sintoma_clave(Enfermedad, Clave),
        \+ member(Clave, Sintomas)
    ->  Razon = falta_sintoma_clave(Clave)
    ;   % Peso insuficiente
        calcula_peso_total(Sintomas, Enfermedad, Peso),
        umbral_minimo(Enfermedad, Umbral),
        Peso < Umbral
    ->  Razon = peso_insuficiente(Peso, Umbral)
    ;   % Reglas incompletas: qué síntomas faltan para la regla más cercana
        regla_mas_cercana(Enfermedad, Sintomas, Faltantes),
        Faltantes \= []
    ->  Razon = reglas_incompletas(Faltantes)
    ;   Razon = causa_desconocida
    ).

% regla_mas_cercana(+Enfermedad, +SintomasUsuario, -SintomasFaltantes)
% Encuentra la regla de la enfermedad a la que le faltan menos síntomas y devuelve qué le falta
regla_mas_cercana(Enfermedad, Sintomas, Faltantes) :-
    findall(NF-FaltantesRegla,
            (regla(_ID, CondPos, CondNeg, Enfermedad, _Desc),
             \+ (member(Neg, CondNeg), member(Neg, Sintomas)),
             subtract(CondPos, Sintomas, FaltantesRegla),
             length(FaltantesRegla, NF)),
            Pares),
    (   Pares = [] -> Faltantes = []
    ;   keysort(Pares, [_-Faltantes|_])   % la regla a la que le faltan menos síntomas
    ).

% Síntomas clave (patognomónicos) por enfermedad
sintoma_clave(covid, perdida_olfato).
sintoma_clave(neumonia, dolor_pecho).
sintoma_clave(alergia, estornudos).
sintoma_clave(gripe, fiebre).
sintoma_clave(resfriado, congestion).

% Síntomas excluyentes por enfermedad
sintoma_excluyente(alergia, fiebre).  % Alergia no cursa con fiebre

% Umbral mínimo de peso por enfermedad
umbral_minimo(gripe, 8).
umbral_minimo(resfriado, 6).
umbral_minimo(covid, 8).
umbral_minimo(alergia, 5).
umbral_minimo(neumonia, 10).

% ============================================================
% MÓDULO DE RECOMENDACIÓN ("¿Qué falta?")
% ============================================================

% recomendar_sintoma(+SintomasParciales, -SintomaRecomendado, -HipotesisCompetidoras, -Explicacion)
% Determina qué síntoma preguntar a continuación para desempatar
recomendar_sintoma(SintomasParciales, SintomaRecomendado, HipotesisCompetidoras, Explicacion) :-
    % 1. Encontrar hipótesis parcialmente activas (con al menos 1 síntoma)
    hipotesis_parciales(SintomasParciales, HipotesisParciales),
    % 2. Filtrar las que están en competencia (peso similar)
    competidoras(HipotesisParciales, SintomasParciales, HipotesisCompetidoras),
    % 3. Encontrar síntomas no preguntados que discriminen mejor
    sintomas_no_preguntados(SintomasParciales, NoPreguntados),
    % 4. Seleccionar el de mayor peso discriminativo
    mejor_discriminador(NoPreguntados, HipotesisCompetidoras, SintomaRecomendado),
    % 5. Generar explicación
    genera_explicacion_recomendacion(SintomaRecomendado, HipotesisCompetidoras, Explicacion).

% hipotesis_parciales(+Sintomas, -ListaParciales)
% Devuelve diagnósticos que tienen al menos 1 síntoma coincidente
hipotesis_parciales(Sintomas, Parciales) :-
    listar_todas_enfermedades(Todas),
    findall(parcial(Diag, Peso, SintomasMatch),
            (member(Diag, Todas),
             Diag \= indeterminado, Diag \= desconocido, Diag \= none,
             findall(S, (member(S, Sintomas), sintoma_enfermedad(S, Diag, P), P > 0), SintomasMatch),
             SintomasMatch \= [],
             calcula_peso(SintomasMatch, Diag, Peso)),
            Parciales).

% competidoras(+Parciales, +Sintomas, -Competidoras)
% Filtra hipótesis con pesos cercanos (en competencia)
competidoras(Parciales, _Sintomas, Competidoras) :-
    (Parciales = [] -> Competidoras = []
    ;   max_peso_parcial(Parciales, MaxPeso),
        UmbralCompetencia is MaxPeso - 3,  % Dentro de 3 puntos del máximo
        include(peso_ge(UmbralCompetencia), Parciales, Competidoras)
    ).

peso_ge(Umbral, parcial(_, Peso, _)) :- Peso >= Umbral.

% sintomas_no_preguntados(+SintomasUsuario, -SintomasNoPreguntados)
sintomas_no_preguntados(Sintomas, NoPreguntados) :-
    all_sintomas_conocidos(Todos),
    subtract(Todos, Sintomas, NoPreguntados).

all_sintomas_conocidos([fiebre, tos, dolor_garganta, congestion, dolor_cabeza,
                       fatiga, perdida_olfato, estornudos, dolor_pecho, dificultad_respirar]).

% mejor_discriminador(+SintomasCandidatos, +HipotesisCompetidoras, -MejorSintoma)
% Selecciona el síntoma que mejor separa las hipótesis competidoras
mejor_discriminador([S|Rest], Hipotesis, Mejor) :-
    mejor_discriminador(Rest, Hipotesis, S, Mejor).

mejor_discriminador([], _, Mejor, Mejor).
mejor_discriminador([S|Rest], Hipotesis, ActualMejor, Mejor) :-
    poder_discriminativo(S, Hipotesis, PoderS),
    poder_discriminativo(ActualMejor, Hipotesis, PoderActual),
    (PoderS > PoderActual ->
        mejor_discriminador(Rest, Hipotesis, S, Mejor)
    ;   mejor_discriminador(Rest, Hipotesis, ActualMejor, Mejor)
    ).

% poder_discriminativo(+Sintoma, +Hipotesis, -Poder)
% Qué tan bien el síntoma separa las hipótesis (varianza de pesos)
poder_discriminativo(Sintoma, Hipotesis, Poder) :-
    findall(Peso,
            (member(parcial(Diag, _, _), Hipotesis),
             sintoma_enfermedad(Sintoma, Diag, Peso)),
            Pesos),
    (Pesos = [] -> Poder = 0
    ;   max_list(Pesos, Max), min_list(Pesos, Min),
        sintoma_peso(Sintoma, Base),
        Poder is Max - Min + Base
    ).

% genera_explicacion_recomendacion(+Sintoma, +Hipotesis, -Explicacion)
genera_explicacion_recomendacion(Sintoma, Hipotesis, Explicacion) :-
    findall(Diag, member(parcial(Diag, _, _), Hipotesis), Nombres),
    atomic_list_concat(Nombres, ', ', NombresStr),
    format(atom(Explicacion),
           'Para diferenciar entre ~w, se recomienda preguntar por "~w" (peso discriminativo mayor).',
           [NombresStr, Sintoma]).

% ============================================================
% PREDICADOS AUXILIARES
% ============================================================

% valida_entrada(+Lista)
valida_entrada(Lista) :-
    is_list(Lista),
    forall(member(X, Lista), ground(X)).

% subset(+Sub, +Super)
subset([], _).
subset([H|T], Super) :-
    memberchk(H, Super),
    subset(T, Super).

% calcula_peso(+Sintomas, +Enfermedad, -PesoTotal)
calcula_peso(Sintomas, Enfermedad, Peso) :-
    findall(P, (member(S, Sintomas), sintoma_enfermedad(S, Enfermedad, P)), Pesos),
    sum_list(Pesos, Peso).

% calcula_peso_total(+Sintomas, +Enfermedad, -PesoTotal)
calcula_peso_total(Sintomas, Enfermedad, Peso) :-
    calcula_peso(Sintomas, Enfermedad, Peso).

% max_peso(+ListaTuplas, -TuplaMax)
max_peso([(ID, Diag, Desc, Peso)|Rest], Max) :-
    max_peso_rest(Rest, (ID, Diag, Desc, Peso), Max).

max_peso_rest([], Max, Max).
max_peso_rest([(ID, Diag, Desc, Peso)|Rest], (BestID, BestDiag, BestDesc, BestPeso), Max) :-
    (Peso > BestPeso ->
        max_peso_rest(Rest, (ID, Diag, Desc, Peso), Max)
    ;   max_peso_rest(Rest, (BestID, BestDiag, BestDesc, BestPeso), Max)
    ).

% max_peso_parcial(+ListaParciales, -MaxPeso)
max_peso_parcial([parcial(_, Peso, _)|Rest], Max) :-
    max_peso_parcial_rest(Rest, Peso, Max).

max_peso_parcial_rest([], Max, Max).
max_peso_parcial_rest([parcial(_, Peso, _)|Rest], CurrentMax, Max) :-
    (Peso > CurrentMax ->
        max_peso_parcial_rest(Rest, Peso, Max)
    ;   max_peso_parcial_rest(Rest, CurrentMax, Max)
    ).

% determina_severidad(+_ReglaID, +Sintomas, -Severidad)
determina_severidad(_ReglaID, Sintomas, Severidad) :-
    (   member(dificultad_respirar, Sintomas),
        member(dolor_pecho, Sintomas)
    ->  Severidad = alta
    ;   member(fiebre, Sintomas),
        member(perdida_olfato, Sintomas)
    ->  Severidad = media_alta
    ;   member(fiebre, Sintomas)
    ->  Severidad = media
    ;   Severidad = baja
    ).

% ============================================================
% PREDICADOS DE CONSULTA DIRECTA PARA PYTHON
% ============================================================

% consultar_diagnostico(+Sintomas, -Diagnostico, -Severidad, -Trace)
% Interfaz simplificada para llamada desde Python
consultar_diagnostico(Sintomas, Diagnostico, Severidad, Trace) :-
    diagnostico(Sintomas, Diagnostico, Severidad, ReglasIDs),
    trace_inferencia(Diagnostico, Sintomas, FiredRules, ProvenFacts, Discarded),
    Trace = trace(FiredRules, ProvenFacts, Discarded, ReglasIDs).

% consultar_recomendacion(+SintomasParciales, -SintomaRecomendado, -HipotesisCompetidoras, -Explicacion)
consultar_recomendacion(Sintomas, SintomaRec, Hipotesis, Explicacion) :-
    recomendar_sintoma(Sintomas, SintomaRec, Hipotesis, Explicacion).

% consultar_diagnostico_texto(+Sintomas, -Diagnostico, -Severidad, -TraceTexto)
% Igual que consultar_diagnostico/4, pero entrega la traza como texto Prolog
% (term_to_atom/2) para que PySwip no pierda los nombres de los átomos.
consultar_diagnostico_texto(Sintomas, Diagnostico, Severidad, TraceTexto) :-
    consultar_diagnostico(Sintomas, Diagnostico, Severidad, Trace),
    term_to_atom(Trace, TraceTexto).

% consultar_recomendacion_texto(+Sintomas, -SintomaRec, -HipotesisTexto, -Explicacion)
% Igual que consultar_recomendacion/4, con las hipótesis serializadas como texto.
consultar_recomendacion_texto(Sintomas, SintomaRec, HipotesisTexto, Explicacion) :-
    consultar_recomendacion(Sintomas, SintomaRec, Hipotesis, Explicacion),
    term_to_atom(Hipotesis, HipotesisTexto).

% listar_todos_sintomas(-Lista)
listar_todos_sintomas(Lista) :-
    all_sintomas_conocidos(Lista).

% listar_todas_enfermedades(-Lista)
listar_todas_enfermedades([gripe, resfriado, covid, alergia, neumonia]).