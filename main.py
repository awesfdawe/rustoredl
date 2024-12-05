import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
@limiter.limit("10/minute")
async def read_index(request: Request):
    return FileResponse("index.html")


class AppInfo(BaseModel):
    app_name: str
    version_name: str
    version_code: int


@app.get("/app/{package_name}", response_class=HTMLResponse)
@limiter.limit("5/minute")
def get_app_info(package_name: str, request: Request):
    app_info_url = (
        f"https://backapi.rustore.ru/applicationData/overallInfo/{package_name}"
    )
    response = requests.get(app_info_url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()["body"]

    app_info = AppInfo(
        app_name=data["appName"],
        version_name=data["versionName"],
        version_code=data["versionCode"],
    )

    download_url = "https://backapi.rustore.ru/applicationData/download-link"
    response = requests.post(
        download_url,
        json={"appId": data["appId"], "firstInstall": True},
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    download_link = response.json()["body"]["apkUrl"]

    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>{app_info.app_name}</title>
        </head>
        <body>
            <h1><a href={download_link}>Скачать {app_info.app_name}</a> Версия: {app_info.version_name} Версия для Obtainium: {app_info.version_code}</h1>
            <h2>Инструкция по добавлению приложений из RuStore:</h2>
            <h3>1. Введите ссылку из адресной строке браузера.</h3>
            <h3>2. Активируйте опцию "Применить регулярное выражение версии ко всей странице".</h3>
            <h3>3. Введите регулярное выражение в поле "Регулярное выражение для извлечения версии": <b>Версия для Obtainium:\s*(\d+)</b></h3>
            <h3>4. Отключите опцию "Согласовать строку версии с версией, обнаруженной в ОС".</h3>
        </body>
    </html>
    """
