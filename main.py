import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from urllib.parse import quote

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
    short_description: str
    version_name: str
    version_code: int
    package_name: str
    company_name: str


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
        short_description=data["shortDescription"],
        version_name=data["versionName"],
        version_code=data["versionCode"],
        package_name=data["packageName"],
        company_name=data["companyName"],
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
    obtainium_link = """{
            "apps": [
                {
                    "id": "% s",
                    "url": "https://rustoredl.023366.xyz/app/% s",
                    "author": "% s",
                    "name": "% s",
                    "additionalSettings": "{\"versionExtractWholePage\":true,\"versionExtractionRegEx\":\"Версия для Obtainium:\\\\s*(\\\\d+)\",\"versionDetection\":false,\"useVersionCodeAsOSVersion\":false,\"about\":\"% s\"}",
                }
            ]
        }""" % (
        app_info.package_name,
        app_info.package_name,
        app_info.company_name,
        app_info.app_name,
        app_info.short_description,
    )
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>{app_info.app_name}</title>
        </head>
        <body>
            <h1><a href={download_link}>Скачать {app_info.app_name}</a> Версия: {app_info.version_name} Версия для Obtainium: {app_info.version_code}</h1>
            <h1><a href="{"obtainium://app/" + obtainium_link}"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" alt="Добавить в obtainium"</img></a></h1>
            <h3>Если у вас возникли трудности с добавлением через кнопку, скопируйте конфигурацию ниже и вставьте её в Obtainium вручную.</h3>
            <textarea readonly>{obtainium_link}</textarea>
        </body>
    </html>
    """
