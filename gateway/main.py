from fastapi import FastAPI, HTTPException, File, UploadFile
import fastapi as _fastapi
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from jwt.exceptions import DecodeError
from pydantic import BaseModel
import requests
import base64
import pika
import logging
import os
import jwt

# Инициализация приложения FastAPI
app = FastAPI()

# Указание схемы аутентификации с использованием OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования (вывод логов уровня INFO)
logging.basicConfig(level=logging.INFO)

# Получение переменных окружения
JWT_SECRET = os.environ.get("JWT_SECRET")  # Секретный ключ для подписи JWT
AUTH_BASE_URL = os.environ.get("AUTH_BASE_URL")  # URL микросервиса аутентификации
RABBITMQ_URL = os.environ.get("RABBITMQ_URL")  # URL для подключения к RabbitMQ

# Установка соединения с RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_URL))  # Подключение к RabbitMQ
channel = connection.channel()  # Создание канала связи
channel.queue_declare(queue='gatewayservice')  # Создание очереди `gatewayservice`

# Функция для проверки и декодирования JWT токена
async def jwt_validation(token: str = _fastapi.Depends(oauth2_scheme)):
    try:
        # Декодирование токена JWT
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except DecodeError:
        # Обработка ошибки декодирования токена
        raise HTTPException(status_code=401, detail="Invalid JWT token")

# Pydantic модели для описания тела запросов
class GenerateUserToken(BaseModel):
    username: str
    password: str

class UserCredentials(BaseModel):
    username: str
    password: str

class UserRegisteration(BaseModel):
    name: str
    email: str
    password: str

class GenerateOtp(BaseModel):
    email: str

class VerifyOtp(BaseModel):
    email: str
    otp: int

# Эндпоинты для работы с сервисом аутентификации

# Эндпоинт для входа пользователя
@app.post("/auth/login", tags=['Authentication Service'])
async def login(user_data: UserCredentials):
    try:
        # Запрос к микросервису аутентификации для получения токена
        response = requests.post(f"{AUTH_BASE_URL}/api/token", json={"username": user_data.username, "password": user_data.password})
        if response.status_code == 200:
            return response.json()  # Успешный ответ с токеном
        else:
            # Обработка ошибки, возвращаемой микросервисом
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        # Если микросервис недоступен
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

# Эндпоинт для регистрации нового пользователя
@app.post("/auth/register", tags=['Authentication Service'])
async def registeration(user_data: UserRegisteration):
    try:
        # Запрос к микросервису аутентификации для регистрации
        response = requests.post(f"{AUTH_BASE_URL}/api/users", json={"name": user_data.name, "email": user_data.email, "password": user_data.password})
        if response.status_code == 200:
            return response.json()  # Успешная регистрация
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

# Эндпоинт для генерации OTP (одноразового пароля)
@app.post("/auth/generate_otp", tags=['Authentication Service'])
async def generate_otp(user_data: GenerateOtp):
    try:
        # Запрос к микросервису для генерации OTP
        response = requests.post(f"{AUTH_BASE_URL}/api/users/generate_otp", json={"email": user_data.email})
        if response.status_code == 200:
            return response.json()  # OTP успешно сгенерирован
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

# Эндпоинт для проверки OTP
@app.post("/auth/verify_otp", tags=['Authentication Service'])
async def verify_otp(user_data: VerifyOtp):
    try:
        # Запрос к микросервису для верификации OTP
        response = requests.post(f"{AUTH_BASE_URL}/api/users/verify_otp", json={"email": user_data.email, "otp": user_data.otp})
        if response.status_code == 200:
            return response.json()  # OTP успешно подтвержден
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

# Запуск приложения для отладки
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)  # Хост и порт, используемые приложением
