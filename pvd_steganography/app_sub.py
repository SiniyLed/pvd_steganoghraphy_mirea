import streamlit as st
import os
import tempfile
from PIL import Image
import hashlib
import random
from pvd_lib import pvd_lib


class SimpleECDSA:
    #упрощенная ЭЦП RSA для интеграции
    @staticmethod
    def generate_keys(key_size=512):
        def is_prime(n, k=128):
            if n < 2: return False
            for _ in range(k):
                a = random.randrange(2, n - 1)
                if pow(a, n - 1, n) != 1:
                    return False
            return True

        def generate_prime(bits):
            while True:
                p = random.getrandbits(bits)
                p |= (1 << bits - 1) | 1
                if is_prime(p):
                    return p

        p = generate_prime(key_size // 2)
        q = generate_prime(key_size // 2)
        n = p * q
        phi = (p - 1) * (q - 1)
        e = 65537
        d = pow(e, -1, phi)

        return (e, n), (d, n)

    @staticmethod
    def hash_message(message):
        if isinstance(message, str):
            message = message.encode('utf-8')
        return int.from_bytes(hashlib.sha256(message).digest(), 'big')

    @staticmethod
    def create_signature(message, private_key):
        d, n = private_key
        message_hash = SimpleECDSA.hash_message(message)
        signature = pow(message_hash, d, n)
        return signature

    @staticmethod
    def verify_signature(message, signature, public_key):
        #проверка эцп
        e, n = public_key
        message_hash = SimpleECDSA.hash_message(message)
        decrypted_hash = pow(signature, e, n)
        return message_hash == decrypted_hash


#сессия
if 'ecdsa_keys' not in st.session_state:
    st.session_state.ecdsa_keys = SimpleECDSA.generate_keys()
if 'extracted_signature' not in st.session_state:
    st.session_state.extracted_signature = None
if 'extracted_message' not in st.session_state:
    st.session_state.extracted_message = None

st.set_page_config(page_title="Stego-ЭЦП", layout="wide")
st.title("Стеганография с ЭЦП")

#ключи в сайдбаре
st.sidebar.header("Ключи ЭЦП")
public_key, private_key = st.session_state.ecdsa_keys
st.sidebar.code(f"Публичный ключ:\ne: {public_key[0]}\nn: ...")
st.sidebar.button("Сгенерировать новые ключи",
                  on_click=lambda: st.session_state.update(ecdsa_keys=SimpleECDSA.generate_keys()))

#основной
tab1, tab2 = st.tabs(["Подписать и спрятать", "Извлечь и проверить"])

with tab1:
    st.header("Создание и скрытие ЭЦП")

    col1, col2 = st.columns(2)

    with col1:
        #сообщение
        message_to_sign = st.text_area(
            "Сообщение для подписи:",
            value="Секретное сообщение для передачи",
            height=100
        )

        if st.button("Создать ЭЦП", type="primary"):
            if message_to_sign:
                #создание эцп
                signature = SimpleECDSA.create_signature(message_to_sign, private_key)
                st.session_state.current_signature = signature
                st.session_state.current_message = message_to_sign

                st.success("ЭЦП создана!")
                st.code(f"Подпись: {signature}")
            else:
                st.error("Введите сообщение для подписи")

    with col2:
        #загрузка изображения-контейнера
        st.subheader("Спрятать подпись в изображении")
        carrier_image = st.file_uploader(
            "Выберите изображение-контейнер",
            type=['png', 'jpg', 'jpeg'],
            key="carrier"
        )

        if carrier_image and hasattr(st.session_state, 'current_signature'):
            #превью картинки
            image = Image.open(carrier_image)
            st.image(image, caption="Изображение-контейнер", use_column_width=True)

            if st.button("Спрятать ЭЦП в изображение", type="secondary"):
                with st.spinner("Прячу подпись..."):
                    try:
                        #создание временного файла
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                            image.save(tmp_img.name)
                            carrier_path = tmp_img.name

                        #создание временного файла с подписью
                        signature_str = f"SIGNATURE:{st.session_state.current_signature}:MESSAGE:{st.session_state.current_message}"
                        # ЯВНО указываем кодировку UTF-8 при записи
                        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', encoding='utf-8') as tmp_sig:
                            tmp_sig.write(signature_str)
                            signature_path = tmp_sig.name

                        #прячем подпись в изображение
                        stego_path = "stego_signed_image.png"
                        pvd = pvd_lib()
                        result = pvd.pvd_embed(carrier_path, signature_path, stego_path)

                        if result:
                            st.success(f"Подпись спрятана! Использовано бит: {result}")

                            # Показываем результат
                            stego_image = Image.open(stego_path)
                            st.image(stego_image, caption="Изображение со скрытой подписью", use_column_width=True)

                            # Кнопка скачивания
                            with open(stego_path, "rb") as file:
                                st.download_button(
                                    label="Скачать изображение со скрытой подписью",
                                    data=file,
                                    file_name="signed_image.png",
                                    mime="image/png"
                                )

                        #чистка
                        os.unlink(carrier_path)
                        os.unlink(signature_path)

                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")

with tab2:
    st.header("Извлечение и проверка ЭЦП")

    col1, col2 = st.columns(2)

    with col1:
        #загрузка оригинального изображения
        original_image_upload = st.file_uploader(
            "Загрузите ОРИГИНАЛЬНОЕ изображение (без подписи)",
            type=['png', 'jpg', 'jpeg'],
            key="original_verify"
        )

        #загрузка стего-изображения
        stego_image_upload = st.file_uploader(
            "Загрузите изображение СО СКРЫТОЙ подписью",
            type=['png', 'jpg', 'jpeg'],
            key="stego_verify"
        )

        if stego_image_upload and original_image_upload:
            #предпросмотр изображений
            original_img = Image.open(original_image_upload)
            stego_img = Image.open(stego_image_upload)

            col_preview1, col_preview2 = st.columns(2)
            with col_preview1:
                st.image(original_img, caption="Оригинальное изображение", use_column_width=True)
            with col_preview2:
                st.image(stego_img, caption="Стего-изображение", use_column_width=True)

            if st.button("Извлечь подпись", type="primary"):
                with st.spinner("Извлекаю подпись..."):
                    try:
                        #сохранение временных файлов
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_orig:
                            original_img.save(tmp_orig.name)
                            original_path = tmp_orig.name

                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_stego:
                            stego_img.save(tmp_stego.name)
                            stego_path = tmp_stego.name

                        #извлечение подписи
                        extracted_path = "extracted_signature.txt"
                        pvd = pvd_lib()

                        #вызов с двумя разными файлами
                        result = pvd.pvd_extract(original_path, extracted_path, stego_path)

                        if result and os.path.exists(extracted_path):
                            #чтение с указанием кодировки UTF-8 и обработкой ошибок
                            try:
                                with open(extracted_path, 'r', encoding='utf-8') as f:
                                    extracted_data = f.read()
                            except UnicodeDecodeError:
                                try:
                                    with open(extracted_path, 'r', encoding='cp1251') as f:
                                        extracted_data = f.read()
                                except UnicodeDecodeError:
                                    with open(extracted_path, 'r', encoding='latin-1') as f:
                                        extracted_data = f.read()

                            #парсинг подписи и сообщения
                            if "SIGNATURE:" in extracted_data and "MESSAGE:" in extracted_data:
                                parts = extracted_data.split(":")
                                if len(parts) >= 4:
                                    signature = int(parts[1])
                                    message = parts[3]

                                    st.session_state.extracted_signature = signature
                                    st.session_state.extracted_message = message

                                    st.success("Подпись извлечена!")
                                    st.info(f"Извлеченное сообщение: {message}")
                                    st.code(f"Извлеченная подпись: {signature}")
                                else:
                                    st.error("Неверный формат извлеченных данных")
                            else:
                                st.error("Не удалось распарсить извлеченные данные")
                                st.code(f"Сырые данные: {extracted_data[:100]}...")

                        #чистка временных файлов
                        os.unlink(original_path)
                        os.unlink(stego_path)
                        if os.path.exists(extracted_path):
                            os.unlink(extracted_path)

                    except Exception as e:
                        st.error(f"Ошибка при извлечении: {str(e)}")

    with col2:
        #проверка подписи
        if st.session_state.extracted_signature and st.session_state.extracted_message:
            st.subheader("Проверка подлинности")

            st.info(f"Сообщение для проверки: {st.session_state.extracted_message}")
            st.code(f"Подпись для проверки: {st.session_state.extracted_signature}")

            if st.button("Проверить подпись", type="secondary", use_container_width=True):
                is_valid = SimpleECDSA.verify_signature(
                    st.session_state.extracted_message,
                    st.session_state.extracted_signature,
                    public_key
                )

                if is_valid:
                    st.success("Подпись ВАЛИДНА! Сообщение подлинное.")
                else:
                    st.error("Подпись НЕВАЛИДНА! Сообщение могло быть изменено.")

#демо
st.markdown("---")
st.header("Как это работает")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Подписание")
    st.markdown("""
    - Создается ЭЦП сообщения
    - Подпись преобразуется в текст
    - Данные готовы к скрытию
    """)

with col2:
    st.subheader("2. Скрытие")
    st.markdown("""
    - Подпись прячется в изображение
    - Используется PVD стеганография
    - Визальное качество сохраняется
    """)

with col3:
    st.subheader("3. Проверка")
    st.markdown("""
    - Подпись извлекается из изображения
    - Проверяется подлинность
    - Гарантируется целостность данных
    """)

st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)
