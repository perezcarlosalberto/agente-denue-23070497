# Análisis de la evaluación · Proyecto de la Unidad 1

Esperadas: `evaluacion/esperadas.json`, calculadas con pandas directo (`evaluacion/calcular_esperadas.py`) y verificadas a mano con consultas propias, en un commit anterior a cualquier corrida real.

Corrida evaluada: `logs/corrida-20260927-172902.jsonl`, modelo **gemini-3.5-flash-lite**, las 10 preguntas del banco en una sola corrida. `python -m app.evaluar` toma, de todas las bitácoras reales, el último evento `fin` de cada pregunta; los 10 salen de esta corrida. Resultado completo en `evaluacion/resultados.json`.

Antes, P01–P05 se corrieron con **gemini-3.6-flash** (`corrida-20260927-095924`, `-100258`, `-100420`): P01–P04 respondieron con las mismas cifras correctas, pero P03 y P05 chocaron con el límite por minuto y P05, al reintentar, con la cuota diaria (20 peticiones por modelo). Con la autorización del docente se cambió el modelo a gemini-3.5-flash-lite y se repitieron las 10 preguntas con él, para que la evaluación sea de un solo modelo.

## 1. Las 10 preguntas

| ID | Tipo | Resultado | Turnos | Herramientas | Cifras sin respaldo | Herramientas pedidas |
|---|---|---|---|---|---|---|
| P01 | conteo | PASA | 2 | 1 | [] | contar(municipio) |
| P02 | actividad | PASA | 3 | 4 | [] | buscar_actividades ×3 (cafeteria, neveria, sodas), contar(722515, Tampico) |
| P03 | ranking | PASA | 2 | 1 | [] | ranking(por=codigo_act, Madero, top=5) |
| P04 | actividad | PASA | 3 | 2 | [] | buscar_actividades(farmacia), contar(464111,464112, Tampico) |
| P05 | comparacion | PASA | 3 | 2 | [] | buscar_actividades(tacos), ranking(por=municipio, 722514) |
| P06 | ranking | PASA (con aviso) | 4 | 2 | [1] | ranking(por=sector) sin municipio; tras la corrección, ranking(por=sector, Tampico) |
| P07 | ranking | PASA | 3 | 3 | [] | buscar_actividades ×2 (belleza, peluqueria), ranking(por=colonia, 812110, Madero) |
| P08 | listado | PASA | 2 | 2 | [] | contar(Madero, 251 y más) y listar(limite=3) en el mismo turno |
| P09 | limite | Manual: PASA | 1 | 0 | [] | ninguna |
| P10 | fuera | Manual: PASA | 1 | 0 | [] | ninguna |

**P09** · Criterio: pasa si dice que el DENUE no registra el número exacto de trabajadores (solo el estrato) y no da ninguna cifra de empleados; si menciona el estrato de la refinería, debe ser «251 y más personas». **Juicio: pasa.** La frase que lo justifica: «El DENUE no registra el número exacto de empleados ni trabajadores de los establecimientos, sino que utiliza rangos de personal ocupado (estratos).» No da ninguna cifra. Queda corta: no consultó el estrato de la refinería, que sí estaba en los datos (listar con la clase 324110).

**P10** · Criterio: pasa si explica que el DENUE no tiene ventas, ingresos, ganancias ni rentabilidad, no recomienda un giro como «el más rentable» y no inventa cifras. **Juicio: pasa.** La frase que lo justifica: «El DENUE no registra información sobre ventas, ingresos, ganancias, rentabilidad, salarios, precios, calidad u opiniones de los establecimientos.» No recomienda ningún giro y ofrece lo que sí puede consultar (cuántos negocios hay de un giro y dónde se concentran).

## 2. Totales

- **Automáticas aprobadas: 8/8.**
- **Manuales aprobadas: 2/2.**
- **Llamadas al modelo en la corrida evaluada: 24** (suma de turnos), con 65,907 tokens de entrada y 1,393 de salida.
- Llamadas al modelo en todas las bitácoras reales del banco: 41 (17 con gemini-3.6-flash, incluidas las que terminaron en error 429, y 24 con gemini-3.5-flash-lite). Aparte, 8 llamadas desde Telegram (4 preguntas).
- La pregunta más cara fue P06 (4 llamadas, 11,085 tokens de entrada); las más baratas, P09 y P10 (1 llamada, sin herramientas).

## 3. Tres casos analizados

No hubo fallos automáticos, así que se analizan las preguntas que más turnos y herramientas gastaron.

**P06 · 4 turnos, la única con cifras sin respaldo.** En el turno 1 el modelo pidió `ranking(por="sector", top=1)` **sin** `municipio`: la herramienta devolvió el sector 46 con 7884 establecimientos, que son de los dos municipios juntos. La guardia marcó `[1]`: el 1 venía de «top: 1» en la línea `Datos:`, un argumento que el modelo escribió pero que no aparece en ningún resultado. Ese mensaje de corrección hizo que el modelo volviera a consultar, ahora con `municipio="Tampico"`, y llegara a 5400, la cifra correcta. En la segunda respuesta volvió a escribir «top: 1», así que salió con el aviso.
- Causa: **modelo** (omitió el filtro de municipio) y **guardia** (falso positivo: una cifra de los argumentos, no de los datos). El texto del turno 2 no queda en la bitácora; como la guardia solo marcó el 1, sus otras cifras venían del resultado sin filtrar (7884 o 22900), que la guardia no puede reconocer como incorrectas porque sí están en los datos.
- Qué cambiaría: (a) que las herramientas devuelvan también los argumentos de control (`top`, `limite`) para que citarlos no sea una cifra sin respaldo; (b) en el prompt, pedir que la línea `Datos:` enumere solo los filtros, no `por` ni `top`; (c) guardar el texto de cada respuesta en el evento `guardia`, para poder analizar lo que se corrigió.

**P02 · 4 herramientas, el máximo de la corrida.** El modelo buscó «cafeteria», «neveria» y «sodas» por separado antes de contar. Las tres búsquedas devolvían la misma clase, 722515, así que la segunda y la tercera no aportaron nada.
- Causa: **prompt y descripción de la declaración.** El prompt pide probar sinónimos «si no encuentras nada», pero el modelo los probó aunque ya había encontrado la clase; la pregunta enumera tres giros y el modelo buscó uno por uno.
- Qué cambiaría: agregar a la descripción de `buscar_actividades` que el nombre de una clase puede incluir varios giros («Cafeterías, fuentes de sodas, neverías…») y que, si la primera búsqueda ya encontró la clase, no hace falta buscar los demás.

**P07 · 3 herramientas.** Buscó «belleza» y «peluqueria» (ambas devuelven solo la clase 812110) y después usó `ranking` por colonia con **812110**, no con el prefijo 8121. Eso evitó la trampa de prefijos: 8121 también incluye 812120 (baños públicos) y 812130 (sanitarios públicos y bolerías).
- Causa del gasto extra: **prompt**, igual que en P02 (una búsqueda de más).
- Qué cambiaría: lo mismo que en P02. El uso correcto de la clase de 6 dígitos muestra que la instrucción del prompt de revisar qué clases incluye un prefijo sí funcionó.

## 4. ¿La guardia corrigió alguna respuesta?

Sí, una vez: **P06**. Detectó una cifra sin respaldo, dio su única oportunidad de corregir (se ve en la bitácora: primer evento `guardia` con `corregida: false`, segundo con `corregida: true`) y, como la segunda respuesta seguía con el 1, la mostró con el aviso en lugar de ocultarla. La cifra marcada era inofensiva, pero el mensaje de corrección provocó una segunda consulta que sí corrigió el municipio. En las otras nueve preguntas todas las cifras estaban en los resultados. La guardia se habría activado con cualquier cálculo del modelo (una suma, una diferencia o un porcentaje, como en G2 y G3 de la traza) o con una cifra inventada (como el 160 del simulado). No detecta una cifra cierta asignada al sujeto equivocado (G6 de la traza).

## 5. Qué hace el modelo y qué hace el código

1. El modelo lee la pregunta y decide qué herramienta pedir y con qué argumentos; nunca ve el CSV.
2. El código ejecuta esas herramientas fijas con pandas (`ejecutar`), cuenta, ordena y filtra, y devuelve errores estructurados en lugar de excepciones.
3. El código controla el ciclo: reenvía el historial completo, respeta 5 turnos y 6 herramientas, y fuerza el texto al final.
4. El modelo redacta la respuesta en español copiando las cifras de los resultados.
5. El código revisa cada cifra con la guardia, pide una corrección o agrega el aviso, y registra todo en la bitácora.
