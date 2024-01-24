from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/icon.png")
async def main():
    return FileResponse("images/unknown-person-icon.png")

@router.get("/logout.png")
async def main():
    return FileResponse("images/door-check-out-icon.png")

@router.get("/secret1.png")
async def main():
    return FileResponse("images/dog_meme.png")

@router.get("/secret2.png")
async def main():
    return FileResponse("images/cat_meme.png")
