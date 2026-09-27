# Traza a mano · Proyecto de la Unidad 1

> Esta parte **no se hace con un asistente de IA**.
>
> 1. Primero prediga a mano, leyendo su propio código.
> 2. Después ejecute su programa y compare.
>
> Si su predicción no coincidió, déjela como estaba y explique la diferencia.

## E.1 El ciclo con el simulado

Pregunta: «¿Cuántas farmacias hay en Tampico?», con los límites normales.

| Turno | Mensajes en el historial al llamar | Qué devuelve el modelo | Qué hace el código | Herramientas usadas | Eventos de la bitácora |
|---|---|---|---|---|---|
| 1 | 3 | "buscar actividades: farmacia" | Busca dentro del csv empresas con el giro "farmacia"  | 1 | inicio, modelo, herramienta |
| 2 | 5 | contar, 464111,464112, Tampico  | Busca con el id las empresas asociadas a Tampico | 2 | modelo, herramienta |
| 3 | 7 | Nada | Restringe las empresas que no cumplen con el criterio | 2 | modelo, guardia |
| 4 | 10 | "Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112).Datos: DENUE 05/2026, INEGI" | Corrige las empresas y las almacena para devolverlas en forma de respuesta | 2 | modelo, guardia, fin |

**(1) Mensajes del historial al terminar:** 

Tiene 10 mensajes al finalizar

**(2) `total` que devolvió `contar`. ¿Por qué la guardia marcó la respuesta del turno 3?** 
Devolvio 160 ya que estas son cifras sin respaldo


**(3) Con `MAX_HERRAMIENTAS = 1`: ¿en qué turno termina, cuántas herramientas se usaron y qué responde? Explique paso a paso.**

Se terminaria en el turno 2, se usó una sola herramienta y responderia "error": "presupuesto agotado: redacta la respuesta con los resultados que ya tienes."

**Comparación con el programa (qué dio y si coincide):**

Comparación turno por turno
| Turno | Mensajes en el historial al llamar | Qué devuelve el modelo | Qué hace el código | Herramientas usadas | Eventos de la bitácora |
|---|---|---|---|---|---|
| 1 | 1, No coincide predije 3 pero en realidad el historial arranca con 1 solo mensaje  | Si coincide, predije que pediria buscar el texto "farmacia" | No coincide, se ejecuta la herramienta de búsqueda | 1, Si coincide predije 1| inicio, modelo, herramienta, si coincide el flujo inicial fue exactamente el esperado |  
| 2 | 3, No coincide predije 5, pero son 3 porque se agregaron la llamada a la herramienta y su resultado | si coincide: predije correctamente los argumentos de la función | Ejecuta el conteo con los IDs encontrados, no coincide | 2, coincide ya llevan 2 herramientas en total | modelo, herramienta, Si coincide sigue el flujo de pedir y ejecutar la herramienta |  
| 3 | 5, no coincide predije 7, el calculo de mensajes acumulados era incorrecto| En Tampico hay 160 farmacias...' No coincide, predije que no devolveria nada pero el modelo intentó dar una respuesta final dando el resultado del guion de  160 | La guardia intercepta la respuesta por contener cifras sin respaldo, no coincide  | 2, Si coincide porque no se llamaron a nuevas herramientas | modelo, guardia si coincide predije que la guardia entraría en acción |  
| 4 |  7, no coincide porque predije 10 | Respuesta: En Tampico hay 154 farmacias...' Si coincide, predije que la respuesta final correcto de los datos de INEGI | La guardia valida los datos y aprueba la correción y finaliza. No coincide | 2, Si coincidé unicamente usó 2 herramientas |  modelo, guardia, fin, si coincide predije correctamente | 

1.-No coincide. En mi predicción escribí:
Tiene 10 mensajes al finalizar, pero esto no es así 
 Al realizar el ultimo turno habia 7 mensajes en el historial. Al final el historial termina con 8 mensajes. El octavo y ultimo mensaje es la respuesta final de texto generada por el modelo.

2.-No coincide en mi predicción escribí:
Devolvio 160 ya que estas son cifras sin respaldo, pero esto no es así.
La herramienta contar devolvió 154. La guardia marcó la respuesta del turno 3 porque el modelo utilizó el 160 que viene en el guion e intentó responder 160 farmacias. La guardia detectó esto en cifras sin respaldo por lo que rechazó la respuesta.

3.-Coincide en el turno y el número de herramientas; no coincide en la respuesta, en mi predicción escribí:
 Se terminaria en el turno 2, se usó una sola herramienta y responderia "error": "presupuesto agotado: redacta la respuesta con los resultados que ya tienes."
El programa dio
Solamente usó una herramienta, "buscar actividades"
"Respuesta: No pude completar la consulta con el presupuesto".
En la llamada 1 el modelo usa buscar actividades farmacia, solo se ha consumido una herramienta permitida.
En la llamada 2, como se alcanzó MAX_HERRAMIENTAS=1 el sistema bloquea el uso de más herramientas y obliga a generar una respuesta final en forzar_texto
Forzar texto pasa a verdadero lo cual llama a la función call y devuelve el texto.
La guardia revisa la respuesta, no detecta cifras sin respaldo y el programa finaliza. No aparece el mensaje "presupuesto agotado: redacta la respuesta con los resultados que ya tienes." porque el sistema detectó el limite y activó el parámetro forzar texto=true. Aquí nunca se llegó a él porque el paso 12 activó forzar_texto antes.


## E.2 La guardia

| Respuesta | `numeros(respuesta)` (predicción) | `cifras_sin_respaldo` (predicción) | Lo que dio el programa | ¿Coincide? |
|---|---|---|---|---|
| G1 | 296, 570 | 0 | 	[] | Coincide en contenido, difiere en la notación (0 contra[]), ya que el resultado se representa con corchetes sin contenido. La guardia no encuentra cifras sin respaldo porque ambos números existen textualmente en los resultados de las herramientas |
| G2 | 274, 296, 570 | 274 |[274] | Coincide en contenido, difiere en la notación ([]). El número 274 se detecta como cifra sin respaldo porque es un cálculo propio del modelo que no aparece en el texto base|
| G3 | 65.8, 866 | 65.8 | 	[65.8] |Coincide en contenido, difiere en la notación ([]) Se lee 65.8 en decimales, no está en la fuente, por lo que se va a cifras sin respaldo|
| G4 | 5, 296, 570, 2026, 722514 | 0 |  [] |Coincide en contenido, difiere en la notación (0 contra[]). MARCA LISTA ignora el 1. y 2. iniciales. Todos los demás números incluyendo el 5 extraído de "05" están en los resultados.|
| G5 | 1,570 | 1,570 | [1570] | Coincide en contenido, difiere en la notación ( [] y ,). CIFRA respeta la coma de miles, extrayendo 1570 el cual no existe en la fuente. |
| G6 | 296, 570 | 0 | [] | Coincide en contenido, difiere en la notación (0 contra[]). La guardia funciona buscando si la cifra existe en la cadena de texto de los resultados sin evaluar el contexto. Como 570 y 296 sí están presentes, aprueba los números a pesar de que el modelo los cruzó de municipio. |

**¿Cuál respuesta es falsa y pasa la guardia? ¿Por qué no la detecta? ¿Qué parte del proyecto sí la detecta?**

La respuesta falsa es la G6. La guardia no la detecta porque guardia.py unicamente verifica la existencia literal de los caracteres numéricos dentro de los resultados devueltos por las herramientas. No tiene la capacidad para analizar a que municipio corresponde cada cifra. La parte del proyecto que si la detecta es "calificar" en "Evaluar.py" ya que si contrasta la afirmación generada contra las respuestas esperadas.

Al ejecutar el programa, calificar arrojó PASA tanto para G1 como para G6, demostrando que mi afirmación anterior era incorrecta.
El error ocurrió porque calificar en evaluar.py evalúa la respuesta buscando unicamente la presencia aislada de los elementos en cifra clave ([570, 296]). Al igual que la guardia, no analiza la estructura de la oración para saber qué cifra le fue asignada a qué municipio. Incluso si se agregaran textos_clave a la respuesta esperada (ej. "Tampico", "Madero"), la prueba pasaría siempre y cuando las palabras y los números aparezcan en cualquier parte del texto.
Por lo tanto, la única parte del proyecto que realmente detecta esta falsedad semántica (el cruce de datos) es la revisión manual (la traza a mano que estamos realizando), ya que requiere comprensión lectora para validar que la cifra se atribuyó al sujeto correcto.

## E.3 Las herramientas sobre `mini_denue.csv`

| Llamada | Resultado (predicción) | Lo que dio el programa | ¿Coincide? |
|---|---|---|---|
| H1 | Total:5. | ok: true, filtros {municipio: "Tampico"}, total: 5 | Coincide para el total de resultados pero no incluia los campos ok y filtros|
| H2 | Total:4. | ok: true, filtros {codigo_act: "4641"}, total: 4 | Coincide para el total de resultados pero no incluia los campos ok y filtros|
| H3 | Total:2. | ok: true, filtros {municipio: "Ciudad Madero", codigo_act: "464111,464112"}, total: 2 | Coincide para el total de resultados pero no incluia los campos ok y filtros|
| H4 | CENTRO (3) y LAS AMERICAS (2). | ok: true, total_filtrado: 5, filas: CENTRO (3), LAS AMERICAS (2) | Coincide para el total de resultados pero no incluia los campos ok y total_filtrado|
| H5 | Datos de TACOS EL GUERO y TAQUERIA DOÑA LUPE. | ok: true, total: 3, mostrados: 2, en este orden: TAQUERIA DOÑA LUPE (11 a 30 personas), CAFE DEL PUERTO (6 a 10 personas) |No coincide, porque listar ordena los resultados de mayor a menor utilizando la columna estrato (el tamaño del negocio por número de empleados) TACOS EL GUERO quedó fuera porque es el más pequeño. Cómo la herramienta recibió el argumento limite=2, la lista se cortó ahí. El programa devuelve total:3 porque existen 3 negocios que cumplen con el prefijo "7225". pero mostrados:2 porque ese fue el límite impuesto en la llamada |
| H6 | Códigos 464111 y 464112. |  ok: true, actividades: 464111 Farmacias sin minisúper (2), 464112 Farmacias con minisúper (1) | Coincidió en las clases extraidas, pero mi predicción omitió que la herramienta tambien devuelve un conteo interno en la respuesta.El resultado incluyó que la clase 464111 (sin minisúper) tiene 2 establecimientos, y la 464112 (con minisúper) tiene 1. |
| H7 | Total:0. | ok: false, error "No hay establecimientos en la colonia 'centro' que cumplan los demás filtros…", valores_validos: [] |No coincide, el programa devolvió ok: false con un error y valores_válidos : [], porque en el código filtrar, las validaciones y sugerencias de colonia se buscan únicamente entre las filas que ya pasaron los filtros previos. Al aplicar primero municipio= "Ciudad Madero", las unicas colonias que quedan son "UNIDAD NACIONAL" y "PRIMERO DE MAYO". Como "Centro no existe en ese subconjunto, lanza un error en lugar de devolver un conteo de 0. Además valores valido sale vacio, porque ninguna de las colonias reales de Madero se parece textualmente a la palabra "centro" como para sugerirla|

**¿Qué enseña H2 sobre los prefijos?**

Demuestra que el filtro de actividades funciona por prefijos y no requiere el código exacto de 6 dígitos. Al ingresar un código más corto, la herramienta agrupa y suma automaticamente todos los establecimientos cuyos códigos más específicos comiencen con esa misma raíz. Existen 4 filas que empiezan con 4641. El PDF indica que  el código se lee de izquierda a derecha, de lo general a lo particular EN la fila 3 del archivo id 3 entró la clase 464113("Comercio al por menor de productos naturistas..."). Por lo tanto, si un usuario pregunta "¿Cuántas farmacias hay", responder 4 sería incorrecto, porque incluye una tienda naturista que no es una farmacia.