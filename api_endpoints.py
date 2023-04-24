import asyncio
from typing import Optional, List
import json
import config
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import copy
import datetime
import firestore
from pytz import timezone
from enum import Enum
import time
import random

tags_metadata = [
    {
        "name": "Teams",
        "description": "Get and update all data related to a teams",
    },
    {
        "name": "Players",
        "description": "Get and update all data related to a players",
    },
    {
        "name": "Leaderboard",
        "description": "Get leaderboards",
    },
    {
        "name": "Other",
        "description": "Other operations",
    },
]


class Holes(BaseModel):
    id: str
    scores: int

class Players(BaseModel):
    name: str
    scores: int
    holes: List[Holes]


class Team(BaseModel):
    id: Optional[str]
    name: str
    time: Optional[datetime.datetime] = None
    pin: Optional[int] = None
    players: Optional[List[Players]] = None
    scores: Optional[int] = None

class Course(str, Enum):
    pub = "pub"
    circus = "circus"



app = FastAPI(title="golf_backend", version="0.0.1", openapi_tags=tags_metadata)
fs = firestore.FirestoreConnection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
timezone_doc = fs.get_document("config", "timezone")

config.timezone = timezone_doc["timezone"]

def basemodels_to_dicts(*args):
    dicts = []
    for arg in args:
        if isinstance(arg, str):
            arg = json.loads(arg)
        elif isinstance(arg, dict):
            pass
        else:
            arg = arg.dict()
        dicts.append(arg)
    return tuple(dicts)


def calculate_team_score(players):
    scores = 0
    for player in players:
        player_score = player.get("scores")
        if player_score:
            scores += int(player_score)
    return scores


# TODO: Document get team
@app.get("/{course}/team/{pin}", tags=["Teams"])
async def get_team(pin: str, course: Course):
    team = fs.query_document(course, "pin", "==", pin)
    return team


# TODO: Document Create Team
@app.post("/{course}/team", tags=["Teams"])
async def create_team(team: Team, course: Course):
    current_datetime = datetime.datetime.now(tz=timezone(config.timezone))
    team, = basemodels_to_dicts(team)
    players = team.get('players') if team.get('players') else {}
    team_list = fs.query_document(course, "pin", ">", "", False)
    pin_set = False
    pin_list = [x.get("pin") for x in team_list if x.get("pin")] if len(team_list) > 0 else []
    while not pin_set:
        pin = team.get('pin') if team.get('pin') else f"{random.randint(1, 10**4-1):{'04d'}}"
        if pin not in pin_list:
            pin_set = True
        "duplicate pin"
        time.sleep(1)
    scores = calculate_team_score(players) if players else 0
    doc_dict = {"name": team["name"], "created_at": current_datetime, "players": players, "pin": pin, "scores": scores}
    fs.create_document(collection=course, **doc_dict)
    return dict(id=0, name=team['name'], pin=pin)


# TODO: Build endpoint
@app.get("/{course}/teams", tags=["Teams"])
async def get_teams(course: Course):
    return "response"


# TODO: Document TeamList Get
@app.get("/{course}/teamlist", tags=["Teams"])
async def get_a_list_of_teams(course: Course):
    teams_list = fs.get_collection(course)
    response = dict(teams=teams_list)
    return response


# TODO: Build endpoint
@app.post("/{course}/leaderboard", tags=["Leaderboard"])
async def get_leaderboard(course: Course):
    return "response"


# TODO: Document Results
@app.post("/{course}/results", tags=["Other"])
async def update_results(team: Team, course: Course):
    team, = basemodels_to_dicts(team)
    team["score"] = calculate_team_score(team["players"])
    new_team_data = fs.upsert_to_document(course, team["id"], players=team["players"], score=team["score"])
    return new_team_data


# TODO: Build endpoint
@app.get("/{course}/alarms", tags=["Other"])
async def get_alarms(course: Course):
    return "response"


# TODO: Build endpoint
@app.post("/{course}/alarm", tags=["Other"])
async def create_alarm(course: Course):
    return "response"


# Test Data
'''f = open("./tests/new_team.json", "r")
new_team_tests_text = f.read()
f.close()
new_team_tests = json.loads(new_team_tests_text)'''
