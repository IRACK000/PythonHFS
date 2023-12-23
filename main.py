import time
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request

from settings import check_user, guest_directory


app = FastAPI()
app.mount("/res", StaticFiles(directory="res"), name="res")

# HTTP 기본 인증을 사용합니다.
security = HTTPBasic()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="templates")


def get_current_directory(credentials: HTTPBasicCredentials = Depends(security)):
    try:
        return check_user(credentials.username, credentials.password)
    except ValueError as _:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def fix_trailing_slash(request: Request):
    # 맨 마지막에 슬래시가 없는 경우 리다이렉션을 수행합니다.
    if not request.url.path.endswith("/"):
        fixed_url = request.url.path + "/"
        return RedirectResponse(fixed_url)
    return None


def get_file_info(file_path: Path):
    file_stat = file_path.stat(follow_symlinks=True)
    modified_timestamp = file_stat.st_mtime
    size = file_stat.st_size
    if size > 1000000000:  # 1GB
        file_size = f"{size / 1000000000:.2f} GB"
    elif size > 1000000:  # 1MB
        file_size = f"{size / 1000000:.2f} MB"
    elif size > 1000:  # 1KB
        file_size = f"{size / 1000:.2f} KB"
    else:
        file_size = f"{size:.2f} Byte"
    modified_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_timestamp))
    return modified_date, file_size


@app.get("/share/link/{file_path:path}")
async def read_searchable_shared_file(request: Request, file_path: str, current_directory: Path = guest_directory):
    return read_files(request, file_path, current_directory / "link")


@app.get("/share/{file_path:path}")
async def read_shared_file(request: Request, file_path: str, current_directory: Path = guest_directory):
    # share 디렉토리에 대한 요청은 인증 없이 진행됩니다.
    if file_path == "link":
        return fix_trailing_slash(request)
    file_location = current_directory / file_path
    if not file_location.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_location)


@app.get("/{file_path:path}")
async def get_files(request: Request, file_path: str, current_directory: Path = Depends(get_current_directory)):
    return read_files(request, file_path, current_directory)


def read_files(request: Request, file_path: str, current_directory: Path = Depends(get_current_directory)):
    # 다른 디렉토리에 대한 요청은 HTTP 헤더를 통한 인증이 필요합니다.
    file_location = current_directory / file_path
    if file_location.is_file():
        # 파일 다운로드를 위한 헤더 설정
        file_name = file_path.split('/')[-1]
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(file_name)}",
        }
        return FileResponse(file_location, headers=headers)
    elif file_location.is_dir():
        # 디렉토리 내용을 HTML로 렌더링
        result = fix_trailing_slash(request)
        if result is not None:
            return result
        items = [{"name": f"{'../'*i}", "url": f"{'../'*i}", "is_directory": True, "size": "Move to Parent", "date": get_file_info(file_location / "../")[0]} for i in (2, 1) if len(file_path.split('/')) > i]
        files = []
        for item in file_location.iterdir():
            date, size = get_file_info(item)
            if item.is_dir():
                items.append({"name": item.name, "url": f"./{item.name}", "is_directory": True, "size": size, "date": date})
            else:
                files.append({"name": item.name, "url": f"./{item.name}", "is_directory": False, "size": size, "date": date})
        items.extend(files)
        return templates.TemplateResponse(
            "directory_listing.html",
            {"request": request, "directory_name": file_location.name if file_location.name else "root", "items": items},
        )
    else:
        raise HTTPException(status_code=404, detail="Resource not found")
