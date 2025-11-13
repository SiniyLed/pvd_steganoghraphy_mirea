import streamlit as st
import os
import tempfile
from PIL import Image
import io
from pvd_lib import pvd_lib

st.set_page_config(
    page_title="PVD Stegano",
    layout="wide"
)

# инициализация состояния сессии
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None
if 'extracted_file_path' not in st.session_state:
    st.session_state.extracted_file_path = None
if 'download_triggered' not in st.session_state:
    st.session_state.download_triggered = False

st.title("My site")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("Встраивание данных")

    original_image = st.file_uploader(
        "Выберите исходное изображение",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        key="original"
    )

    secret_file = st.file_uploader(
        "Выберите файл для скрытия",
        type=['txt', 'pdf', 'png', 'jpg', 'zip'],
        key="secret"
    )

    if original_image and secret_file:
        st.subheader("Предпросмотр изображения")
        image = Image.open(original_image)
        st.image(image, caption="Исходное изображение", use_column_width=True)

        if st.button("Встроить данные в изображение", type="primary"):
            with st.spinner("Встраиваю данные..."):
                try:
                    # cохранение временных файлов
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                        image.save(tmp_img.name)
                        original_path = tmp_img.name

                    with tempfile.NamedTemporaryFile(delete=False) as tmp_secret:
                        tmp_secret.write(secret_file.getvalue())
                        secret_path = tmp_secret.name

                    result_path = "hidden_image.png"

                    pvd = pvd_lib()
                    result = pvd.pvd_embed(original_path, secret_path, result_path)

                    if result:
                        st.success(f"Данные успешно встроены! Встроено бит: {result}")

                        st.subheader("Результат")
                        result_image = Image.open(result_path)
                        st.image(result_image, caption="Изображение со скрытыми данными", use_column_width=True)

                        with open(result_path, "rb") as file:
                            btn = st.download_button(
                                label="Скачать изображение со скрытыми данными",
                                data=file,
                                file_name="hidden_image.png",
                                mime="image/png"
                            )

                    os.unlink(original_path)
                    os.unlink(secret_path)

                except Exception as e:
                    st.error(f"Ошибка при встраивании: {str(e)}")

with col2:
    st.header("Извлечение данных")

    stego_image = st.file_uploader(
        "Выберите изображение со скрытыми данными",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        key="stego"
    )

    ref_image_extract = st.file_uploader(
        "Выберите оригинальное изображение (опционально)",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        key="ref_extract"
    )

    if stego_image:
        st.subheader("Предпросмотр стего-изображения")
        stego_img = Image.open(stego_image)
        st.image(stego_img, caption="Стего-изображение", use_column_width=True)

        # Кнопка для извлечения
        if st.button("Извлечь скрытые данные", type="secondary"):
            with st.spinner("Извлекаю данные..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_stego:
                        stego_img.save(tmp_stego.name)
                        stego_path = tmp_stego.name

                    ref_path = None
                    if ref_image_extract:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_ref:
                            ref_img = Image.open(ref_image_extract)
                            ref_img.save(tmp_ref.name)
                            ref_path = tmp_ref.name
                    else:
                        # если оригинал не загружен, используем стего-изображение как референс
                        ref_path = stego_path

                    extracted_path = "extracted.bin"

                    pvd = pvd_lib()
                    result = pvd.pvd_extract(ref_path, extracted_path, stego_path)

                    if result and os.path.exists(extracted_path):
                        st.success(f"Данные успешно извлечены! Извлечено бит: {result}")

                        st.session_state.extracted_file_path = extracted_path
                        st.session_state.extracted_content = open(extracted_path, "rb").read()

                        # автоматический запуск обработки извлеченного контента
                        st.session_state.download_triggered = True

                        file_size = len(st.session_state.extracted_content)
                        st.info(f"Размер извлеченных данных: {file_size} байт")

                        # определение типа файла
                        file_type = "бинарный файл"
                        if st.session_state.extracted_content.startswith(b'%PDF'):
                            file_type = "PDF документ"
                        elif st.session_state.extracted_content.startswith(b'PK'):
                            file_type = "ZIP архив"
                        elif b'<?xml' in st.session_state.extracted_content[:100]:
                            file_type = "XML файл"
                        elif all(c < 128 for c in st.session_state.extracted_content[:100]):
                            file_type = "текстовый файл"

                        st.write(f"Тип файла: {file_type}")

                    else:
                        st.error("Не удалось извлечь данные или файл не найден")

                    os.unlink(stego_path)
                    if ref_path and ref_path != stego_path:
                        os.unlink(ref_path)

                except Exception as e:
                    st.error(f"Ошибка при извлечении: {str(e)}")

# раздел для автоматического запуска извлеченного контента
if st.session_state.download_triggered and st.session_state.extracted_content:
    st.markdown("---")
    st.header("Автоматическая обработка извлеченных данных")

    file_extension = ".bin"
    if st.session_state.extracted_content.startswith(b'%PDF'):
        file_extension = ".pdf"
    elif st.session_state.extracted_content.startswith(b'PK'):
        file_extension = ".zip"
    elif st.session_state.extracted_content.startswith(b'\x89PNG'):
        file_extension = ".png"
    elif st.session_state.extracted_content.startswith(b'JFIF'):
        file_extension = ".jpg"

    filename = f"extracted_secret{file_extension}"

    st.download_button(
        label=f"Скачать извлеченный файл ({filename})",
        data=st.session_state.extracted_content,
        file_name=filename,
        mime="application/octet-stream"
    )

    try:
        # пробуем декодировать как текст (чет не работает)
        text_content = st.session_state.extracted_content.decode('utf-8')
        if all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:\n\r\t' for c in
               text_content[:1000]):
            st.subheader("Текстовое содержимое:")
            st.text_area("Извлеченный текст", text_content, height=200)
    except:
        pass

    if file_extension in ['.png', '.jpg', '.jpeg']:
        try:
            image = Image.open(io.BytesIO(st.session_state.extracted_content))
            st.subheader("Извлеченное изображение:")
            st.image(image, caption="Извлеченное изображение", use_column_width=True)
        except:
            pass

st.sidebar.markdown("## Статус системы")
if st.session_state.extracted_content:
    st.sidebar.success("Данные извлечены и готовы")
else:
    st.sidebar.info("Ожидание загрузки файлов")

# CSS для красоты
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        margin-top: 10px;
    }
    .uploadedFile {
        border: 2px solid #e6e6e6;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)
