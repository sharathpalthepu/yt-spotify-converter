import feedparser
import spotipy
import sys
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except:
    pass


def get_rss_url(url):
    playlist_id = url.split("list=")[1]
    rss_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    return rss_url


def discover_feed(rss_url):
    try:
        d = feedparser.parse(rss_url)
        if d.bozo:
            return None, "No feed found at given url."
        return d, None
    except:
        return None, "Failed to fetch feed. Please try again!"


def get_entries(feed):
    res = []
    for entry in feed.entries:
        title = entry.title
        author = entry["author_detail"]["name"]
        song = {"title": title, "artist": author}
        res.append(song)
    return res


def a(test_str):
    ret = ""
    skip1c = 0
    skip2c = 0
    for i in test_str:
        if i == "[":
            skip1c += 1
        elif i == "(":
            skip2c += 1
        elif i == "]" and skip1c > 0:
            skip1c -= 1
        elif i == ")" and skip2c > 0:
            skip2c -= 1
        elif skip1c == 0 and skip2c == 0:
            ret += i
    return ret


def search_spotify(search_term, token):
    r = requests.get(f"https://api.spotify.com/v1/search?q={search_term}&type=track%2Cepisode%2Cshow",   headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },)

    results = r.json()
    items = results["tracks"]["items"]
    if len(items) > 0:
        return items[0]["uri"]
    return None


def search_spotify_handler(artist, title, token):
    search_term = title
    search_term = a(search_term)

    search_term = search_term.replace("-", "")
    res = search_spotify(search_term, token)
    if res:
        return res
    search_term = search_term.replace("&", "ft")
    res = search_spotify(search_term, token)
    if res:
        return res
    search_term = search_term.replace("ft", "feat. ")
    res = search_spotify(search_term, token)
    if res:
        return res
    search_term = search_term.replace("feat.", "with ")
    res = search_spotify(search_term, token)
    if res:
        return res
    
    split_term = a(title).split("-")
    if len(split_term) >= 2:
        res = search_spotify(split_term[0], token)
        if res:
            return res
        res = search_spotify(split_term[1], token)
        if res:
            return res
    return None


def spotify_links(songs, token):
    res = []
    for song in songs:
        link = search_spotify_handler(song["artist"], song["title"], token)
        if link:
            res.append(link)

    return res


def fill_playlist(links, id, token):
    url = f"https://api.spotify.com/v1/playlists/{id}/tracks"

    data = json.dumps({"uris": links})
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=data,
    )

    if r.status_code == 201:
        return True
    else:
        return False


def create_playlist(links, id, name, token):
    data = json.dumps(
        {"name": name, "description": "nice songs", "public": True})
    url = f"https://api.spotify.com/v1/users/{id}/playlists"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=data,
    )
    if r.status_code == 201:
        playlist_link = r.json()["external_urls"]["spotify"]
        playlist_id = r.json()["id"]

        res = fill_playlist(links, playlist_id, token)
        return playlist_link
