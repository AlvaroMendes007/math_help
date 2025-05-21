#rodar o streamlit (frontend do python dentro do colab)
# %%writefile app.py
import streamlit as st
import os
import base64
from google.genai import types
from PIL import Image
import io
from google import genai
import uuid


# os.environ['GOOGLE_API_KEY'] = userdata.get('GOOGLE_API_KEY')
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Verifica se a chave da API está definida. Se não estiver, levanta um erro.
if not GOOGLE_API_KEY:
    st.error("A variável de ambiente GOOGLE_API_KEY não está definida. Por favor, configure-a.")
    st.stop() # Para a execução do Streamlit se a chave da API não estiver presente

# Configura a API do Gemini com a chave fornecida.
client = genai.Client(api_key=GOOGLE_API_KEY)

# Define os modelos a serem usados para visão (imagem) e texto.
model_vision = 'gemini-2.0-flash'
model_text = 'gemini-2.0-flash'

# Configurações de chat para o modelo de visão.
# A instrução do sistema guia o comportamento do modelo.
chat_config_vision = types.GenerateContentConfig(
    system_instruction="""Você é um professor de um pré adolescente que não tem muito conhecimento e ele é surdo,
    então explique de forma fácil, se puder usar imagens e fórmulas de como chegar no resultado final com exemplos.
    Evite muitas palavras, porque ele não consegue ler e entender muito. Caso faça pergunta fora da matemática responda: A pergunta deve ser de matemática""",
)

# Configurações de chat para o modelo de texto.
# A instrução do sistema é a mesma para garantir consistência na explicação.
chat_config_text = types.GenerateContentConfig(
    system_instruction="""Você é um professor de um pré adolescente que não tem muito conhecimento e ele é surdo,
    então explique de forma fácil, se puder usar imagens e fórmulas de como chegar no resultado final com exemplos.
    Evite muitas palavras, porque ele não consegue ler e entender muito. Caso faça pergunta fora da matemática responda: A pergunta deve ser de matemática""",
)

# Dicionário para armazenar estados de usuário (não usado diretamente neste frontend simples,
# mas mantido para compatibilidade com o código original).
user_states = {}

def is_base64_encoded_image(s):
    """
    Verifica heuristicamente se uma string parece ser uma imagem PNG/JPEG codificada em base64.
    Uma verificação mais robusta é feita tentando decodificar e verificar o cabeçalho.
    """
    if not isinstance(s, str) or len(s) < 20:
        return False
    try:
        # Tenta decodificar a string base64.
        decoded_bytes = base64.b64decode(s, validate=True)
        # Tenta abrir os bytes decodificados como uma imagem para uma verificação robusta.
        Image.open(io.BytesIO(decoded_bytes))
        return True
    except (base64.binascii.Error, IOError, OSError):
        # Se a decodificação ou a abertura da imagem falhar, não é uma imagem base64 válida.
        return False

def get_math_expression(input_data):
    """
    Tenta extrair uma expressão matemática de uma imagem codificada em base64 ou de um texto.
    """
    response_text = ""
    # Verifica se a entrada é uma imagem codificada em base64.
    if is_base64_encoded_image(input_data):
        st.info("Entrada identificada como imagem. Extraindo expressão...")
        # Define o prompt para extrair a expressão matemática da imagem.
        prompt_image = "Identifique a principal expressão matemática presente nesta imagem. Apenas a expressão matemática."

        # Remove o prefixo "data:image/png;base64," ou "data:image/jpeg;base64," se presente.
        if "," in input_data:
            base64_data = input_data.split(",")[1]
        else:
            base64_data = input_data

        # Decodifica a string base64 em bytes.
        image_bytes = base64.b64decode(base64_data)

        # Salva a imagem temporariamente para upload para o Google GenAI Files API.
        # Usa uuid para garantir um nome de arquivo único.
        temp_filename = f"temp_image_{uuid.uuid4()}.png"
        with open(temp_filename, "wb") as f:
            f.write(image_bytes)

        # Faz o upload do arquivo para o serviço de arquivos do Google GenAI.
        my_file = client.files.upload(file=temp_filename)
        # Remove o arquivo temporário após o upload.
        os.remove(temp_filename)

        # Prepara o conteúdo para o modelo de visão: o arquivo da imagem e o prompt.
        contents = [my_file, prompt_image]
        # Gera o conteúdo usando o modelo de visão com a configuração de chat.
        response = client.models.generate_content(
            model=model_vision,
            contents=contents,
            config=chat_config_vision # Usando generation_config para as configurações de chat
        )
        response_text = response.text.strip()
    else:
        st.info("Entrada identificada como texto. Identificando expressão...")
        # Define o prompt para identificar a expressão matemática no texto.
        prompt_text = f"Identifique a principal expressão matemática em: '{input_data}'. Apenas a expressão matemática."
        # Prepara o conteúdo para o modelo de texto: apenas o prompt.
        contents = [prompt_text]
        # Gera o conteúdo usando o modelo de texto com a configuração de chat.
        response = client.models.generate_content(
            model=model_text,
            contents=contents,
            config=chat_config_text # Usando generation_config para as configurações de chat
        )
        response_text = response.text.strip()

    return response_text

def generate_example(expression):
    """
    Gera um exemplo visual ou textual simples para a expressão, levando em conta a configuração do chat.
    """
    st.info("Gerando exemplo da expressão...")
    prompt = f"Gere um exemplo muito simples e visualmente intuitivo para uma criança que não sabe ler entender a seguinte expressão matemática: '{expression}'. Use o mínimo de texto possível, focando em símbolos e representações visuais. Se for uma operação, mostre a operação acontecendo com objetos simples. Se for um conceito (como potência), mostre uma representação básica. A resposta deve ser concisa e adequada para uma criança."
    response = client.models.generate_content(model=model_text, contents=[prompt], config=chat_config_text)
    return response.text.strip()

def get_definitive_answer(expression):
    """
    Retorna a resposta definitiva para a expressão, levando em conta a configuração do chat.
    """
    st.info("Calculando a resposta definitiva...")
    prompt = f"Qual o resultado da seguinte expressão matemática: '{expression}'? Responda com o valor numérico ou a simplificação, de forma clara e concisa."
    response = client.models.generate_content(model=model_text, contents=[prompt], config=chat_config_text)
    return response.text.strip()

# --- Frontend Streamlit ---

# Define o título da aplicação Streamlit.
st.title("👨‍🏫 Resolutor de Problemas Matemáticos com IA")
st.markdown("Bem-vindo! Insira sua questão matemática como texto ou envie uma imagem para que a IA a resolva e explique.")

# Área de entrada de texto para a questão matemática.
math_question_text = st.text_area("✍️ Digite sua questão matemática aqui:", height=150, placeholder="Ex: Quanto é 2 + 2 * 3?")

# Uploader de arquivos para imagens.
uploaded_image = st.file_uploader("📸 Ou envie uma imagem com a questão:", type=["png", "jpg", "jpeg"])

# Cria um contêiner vazio para exibir os resultados.
# Isso permite que o conteúdo seja limpo e substituído dinamicamente.
if 'output_placeholder_container' not in st.session_state:
    st.session_state.output_placeholder_container = st.empty()

# Botões para submissão.
col1, col2 = st.columns(2) # Cria duas colunas para os botões

with col1:
    text_submit_button = st.button("🚀 Resolver Questão de Texto")
with col2:
    image_submit_button = st.button("🖼️ Resolver Questão de Imagem")

# Lógica para processar a submissão de texto.
if text_submit_button:
    # Limpa o conteúdo anterior do placeholder.
    st.session_state.output_placeholder_container.empty()
    with st.session_state.output_placeholder_container:
        if math_question_text:
            try:
                # Chama as funções do backend para processar a questão de texto.
                expression = get_math_expression(math_question_text)
                example = generate_example(expression)
                answer = get_definitive_answer(expression)

                # Exibe os resultados.
                st.success("✅ Solução recebida para questão de texto!")
                st.markdown(f"### Expressão Identificada:")
                st.write(expression)
                st.markdown(f"### Exemplo para Crianças:")
                st.write(example)
                st.markdown(f"### Resposta Definitiva:")
                st.write(answer)
            except Exception as e:
                st.error(f"❌ Ocorreu um erro ao processar a questão de texto: {e}")
        else:
            st.warning("⚠️ Por favor, digite uma questão matemática no campo de texto.")

# Lógica para processar a submissão de imagem.
if image_submit_button:
    # Limpa o conteúdo anterior do placeholder.
    st.session_state.output_placeholder_container.empty()
    with st.session_state.output_placeholder_container:
        if uploaded_image:
            try:
                # Lê a imagem como bytes e a codifica em base64.
                image_bytes = uploaded_image.getvalue()
                encoded_image = base64.b64encode(image_bytes).decode("utf-8")

                # Exibe a imagem carregada para confirmação visual.
                st.image(uploaded_image, caption="Imagem Carregada", use_column_width=True)

                # Chama as funções do backend para processar a questão da imagem.
                expression = get_math_expression(encoded_image)
                example = generate_example(expression)
                answer = get_definitive_answer(expression)

                # Exibe os resultados.
                st.success("✅ Solução recebida para questão de imagem!")
                st.markdown(f"### Expressão Identificada:")
                st.write(expression)
                st.markdown(f"### Exemplo para Crianças:")
                st.write(example)
                st.markdown(f"### Resposta Definitiva:")
                st.write(answer)
            except Exception as e:
                st.error(f"❌ Ocorreu um erro ao processar a imagem: {e}")
        else:
            st.warning("⚠️ Por favor, envie uma imagem com a questão matemática.")