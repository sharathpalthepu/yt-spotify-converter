from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional
import requests
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.crawler import *
import os
import time


try:
    from dotenv import load_dotenv

    load_dotenv()
except:
    pass


templates = Jinja2Templates(directory="templates")
app = FastAPI()


@app.get("/")
def home(
    request: Request,
):
    auth = SpotifyOAuth(
        os.getenv("CLIENT_ID"),
        os.getenv("CLIENT_SECRET"),
        os.getenv("CALLBACK_URL"),
        scope="user-top-read,user-library-read,playlist-modify-public,playlist-modify-private",
    )
    auth_url = auth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback")
def callback(request: Request, code: Optional[str] = None):
    auth = SpotifyOAuth(
        os.getenv("CLIENT_ID"),
        os.getenv("CLIENT_SECRET"),
        os.getenv("CALLBACK_URL"),
        scope="user-top-read,user-library-read,playlist-modify-public,playlist-modify-private",
    )
    token = auth.get_access_token(code)

    res = RedirectResponse("/app")
    res.set_cookie("at", token["access_token"])
    res.set_cookie("rt", token["refresh_token"])
    res.set_cookie("ea", token["expires_at"])
    res.set_cookie("token", token)
    return res


@app.get("/app")
def render_app(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/make")
def make(
    request: Request,
    name: str = Form(...),
    link: str = Form(...),
    token: Optional[str] = Cookie(None),
):

    token = eval(token)
    access_token = token["access_token"]
    refresh_token = token["refresh_token"]
    expires_at = token["expires_at"]

    _, authorized = get_token(access_token, refresh_token, expires_at)

    if not authorized:
        res = RedirectResponse("/")
        res.status_code = 302
        return res
    id = get_user(access_token)

    rss_url = get_rss_url(link)
    feed, err = discover_feed(rss_url)

    if not err:
        songs = get_entries(feed)

        links = spotify_links(songs, access_token)

        playlist_link = create_playlist(links, id, name, access_token)

        if playlist_link == None:
            return "Please try again."
        res = RedirectResponse(playlist_link)
        res.status_code = 302
        return res
    else:
        return "Please try again."


def get_token(access_token, refresh_token, expires_at):
    now = int(time.time())
    is_token_expired = int(expires_at) - now > 3600
    token_info = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }
    if access_token == None or refresh_token == None or expires_at == None:
        return token_info, False
    if is_token_expired:
        return token_info, False
    return token_info, True


def get_user(access_token):

    r = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user = None
    if r.status_code == 200:
        user = r.json()
        id = user["id"]
        return id
    return None
