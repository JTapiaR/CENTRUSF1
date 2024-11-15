import streamlit as st
import openai
from openai import OpenAI
import pandas as pd
import requests
from dotenv import load_dotenv
import os
from newspaper import Article

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configura tu clave de OpenAI y de la API de noticias desde el .env
openai_api_key = os.getenv("OPENAI_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

# Verificar que las claves de API están disponibles
if not openai_api_key or not news_api_key:
    st.error("Por favor, asegúrate de que las claves de API de OpenAI y News API estén configuradas en el archivo .env.")
    st.stop()

# Configurar la clave de API de OpenAI
openai.api_key = openai_api_key

# Selección de idioma
language = st.sidebar.selectbox("Selecciona el idioma / Select Language", ("Español", "English"))

# Textos en español e inglés
texts = {
    "Español": {
        "title": "Búsqueda y Resumen de Noticias",
        "keywords": "Define palabras clave (e.g., desastres naturales, escolaridad, sequía, salud):",
        "num_results": "Define el número de resultados para analizar:",
        "search_results": "Resultados de búsqueda",
        "search_button": "Buscar noticias",
        "include": "Incluir",
        "generate_summary": "Generar Resúmenes de Noticias",
        "summary_prompt": "Hazme un resumen de un párrafo del siguiente texto con la siguiente información: año, fecha, evento, población afectada (expresada en un número y su unidad de medida). Texto: ",
        "collect_info": "Recopilación de Información de las Noticias",
        "show_results": "Mostrar Resultados",
        "download_csv": "Descargar CSV",
        "no_articles_found": "No se encontraron artículos. Intenta con otras palabras clave.",
        "api_error": "Error al obtener los datos de la API de noticias.",
        "no_articles_selected": "No se ha seleccionado ninguna noticia para análisis."
    },
    "English": {
        "title": "News Search and Summary",
        "keywords": "Define keywords (e.g., natural disasters, education, drought, health):",
        "num_results": "Define the number of results to analyze:",
        "search_results": "Search Results",
        "search_button": "Search News",
        "include": "Include",
        "generate_summary": "Generate News Summaries",
        "summary_prompt": "Give me a one-paragraph summary of the following text with the following information: year, date, event, affected population (expressed as a number and unit of measure). Text: ",
        "collect_info": "Collection of News Information",
        "show_results": "Show Results",
        "download_csv": "Download CSV",
        "no_articles_found": "No articles found. Try different keywords.",
        "api_error": "Error fetching data from News API.",
        "no_articles_selected": "No news articles selected for analysis."
    }
}

# Configuración de la aplicación
st.title(texts[language]["title"])

# Paso 1: Definir palabras clave
keywords = st.text_input(texts[language]["keywords"])

# Paso 2: Definir el número de resultados
num_results = st.number_input(texts[language]["num_results"], min_value=1, step=1, value=5)

if "data" not in st.session_state:
    st.session_state.data = []

if "seleccionadas" not in st.session_state:
    st.session_state.seleccionadas = []

if keywords:
    st.subheader(texts[language]["search_results"])
    if st.button(texts[language]["search_button"]):
        url = f"https://newsapi.org/v2/everything?q={keywords}&pageSize={num_results}&apiKey={news_api_key}&language=es"
        response = requests.get(url)
        
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            if articles:
                st.session_state.data = []  # Reiniciar datos
                for article in articles:
                    titulo = article.get("title", "")
                    enlace = article.get("url", "")
                    fecha = article.get("publishedAt", "")
                    descripcion = article.get("description", "") or ""
                    contenido = article.get("content", "") or ""
                    st.session_state.data.append({
                        "Título": titulo,
                        "Fecha": fecha,
                        "Descripción": descripcion,
                        "Contenido": contenido,
                        "Enlace": enlace
                    })
            else:
                st.warning(texts[language]["no_articles_found"])
        else:
            st.error(texts[language]["api_error"])

if st.session_state.data:
    st.write(texts[language]["search_results"])
    for i, noticia in enumerate(st.session_state.data):
        checkbox_label = f"**{noticia['Título']}**\n\nFecha: {noticia['Fecha']}\n\n{noticia['Descripción']}\n\n"
        if st.checkbox(checkbox_label, key=f"noticia_{i}"):
            if noticia not in st.session_state.seleccionadas:
                st.session_state.seleccionadas.append(noticia)
        else:
            if noticia in st.session_state.seleccionadas:
                st.session_state.seleccionadas.remove(noticia)

# Paso 7: Generar resumen y extracción automática de información con OpenAI
def obtener_informacion(texto, lang):
    responses = []
    prompt = (
        f"Extrae la siguiente información del texto: año, fecha, estado, municipio, localidad, "
        f"población afectada (en número y unidad de medida), evento, efecto, y acciones después del efecto (si aplica). "
        f"Texto: {texto}"
    )
    try:
        response =client.chat.completions.create(
            model="gpt-4",  # Asegúrate de que tienes acceso a GPT-4
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae información clave de textos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        text_response = response.choices[0].message.content
        responses.append(text_response.strip())
    except Exception as e:
            print(e)
            responses.append("")
    return responses

st.subheader(texts[language]["generate_summary"])
informacion = []

if st.session_state.seleccionadas:
    for noticia in st.session_state.seleccionadas:
        # Intentar obtener el contenido del artículo desde el enlace
        texto_resumen = ""
        try:
            article = Article(noticia['Enlace'], language='es')
            article.download()
            article.parse()
            texto_resumen = article.text
        except Exception as e:
            st.error(f"Error al obtener el contenido del enlace: {e}")
            # Si falla, usar el contenido o descripción proporcionados por la API
            texto_resumen = noticia.get("Contenido", "") or noticia.get("Descripción", "")
        
        if not texto_resumen:
            # Si no hay contenido ni descripción, proporcionar el enlace
            texto_resumen = f"Visita el enlace para más detalles: {noticia['Enlace']}"
        
        info_texto = obtener_informacion(texto_resumen, language)
        informacion.append({
            "Enlace": noticia["Enlace"],
            "Título": noticia["Título"],
            "Información Extraída": info_texto
        })
        st.write(f"**Información extraída de '{noticia['Título']}':**\n{info_texto}\n")
else:
    st.write(texts[language]["no_articles_selected"])

# Paso 5: Mostrar la información extraída
st.subheader(texts[language]["collect_info"])
if informacion:
    if st.button(texts[language]["show_results"]):
        df = pd.DataFrame(informacion)
        st.write(df)
        st.download_button(texts[language]["download_csv"], df.to_csv(index=False), "resultados.csv", "text/csv")
else:
    st.write(texts[language]["no_articles_selected"])