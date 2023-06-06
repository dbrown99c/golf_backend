from typing import Optional, List, Any
import json
import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from pytz import timezone
from enum import Enum
import time
import random

import mongo

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
    time: Optional[datetime] = None
    pin: Optional[int] = None
    players: Optional[List[Players]] = None
    scores: Optional[int] = None


class Course(str, Enum):
    pub = "pub"
    circus = "circus"


class Leaderboard_Type(str, Enum):
    player = "player"
    team = "team"


class Alarm(BaseModel):
    course: str
    hole: int
    id: Optional[str]
    state: Optional[Any]


app = FastAPI(title="golf_backend", version="0.0.1", openapi_tags=tags_metadata)
db = mongo.MongoConnection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# timezone_doc = db.get_document("config", "timezone")
# config.timezone = timezone_doc["timezone"]


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
    team = db.query_document(course, "pin", "==", pin)
    return team


# TODO: Document Create Team
@app.post("/{course}/team", tags=["Teams"])
async def create_team(team: Team, course: Course):
    current_datetime = datetime.now(tz=timezone(config.timezone))
    team, = basemodels_to_dicts(team)
    players = team.get('players') if team.get('players') else {}
    team_list = db.query_document(course, "pin", ">", "", False)
    pin_set = False
    pin_list = [x.get("pin") for x in team_list if x.get("pin")] if len(team_list) > 0 else []
    while not pin_set:
        pin = team.get('pin') if team.get('pin') else f"{random.randint(1, 10 ** 4 - 1):{'04d'}}"
        if pin not in pin_list:
            pin_set = True
        "duplicate pin"
        time.sleep(1)
    scores = calculate_team_score(players) if players else 0
    doc_dict = {"name": team["name"], "created_at": current_datetime, "players": players, "pin": pin, "scores": scores}
    db.create_document(collection=course, **doc_dict)
    for _ in Course:
        db.delete_old_docs(_)
    return dict(id=0, name=team['name'], pin=pin)


@app.get("/teams", tags=["Teams"])
async def get_teams():
    base_list = []
    complete_limit = (datetime.now(tz=timezone(config.timezone)) - timedelta(hours=12)).replace(tzinfo=None)
    for course in Course:
        course_list = db.get_collection(course)
        for x in course_list:
            if x["created_at"] <= complete_limit and len(x.get("players", [])[0].get("holes", [])) < 9:
                db.delete_document(course, x["id"])
            else:
                x["course"] = course
                base_list.append(x)
    return base_list


@app.get("/teams_twentyfour", tags=["Teams"])
async def get_twentyfour_teams():
    base_list = []
    dayago = datetime.now(tz=timezone(config.timezone)) - timedelta(days=1)
    for course in Course:
        course_list = db.query_document(course, "created_at", ">=", dayago, False)
        for x in course_list:
            x["course"] = course
            base_list.append(x)
    return base_list


# TODO: Document TeamList Get
@app.get("/{course}/teamlist", tags=["Teams"])
async def get_a_list_of_teams(course: Course):
    teams_list = db.get_collection(course)
    response = dict(teams=teams_list)
    return response


# TODO: Document leaderboard
@app.get("/{course}/leaderboard/{ltype}", tags=["Leaderboard"])
async def get_leaderboard(ltype: Leaderboard_Type, course: Course):
    weekago = datetime.now(tz=timezone(config.timezone)) - timedelta(days=7)
    result_list = db.query_document(course, "created_at", ">=", weekago, False)
    if ltype == 'team':
        weekresults = [{'team': x.get('name'), 'scores': x.get('scores')} for x in result_list if
                       len(x.get("players", [])[0].get("holes", [])) == 9]
        weekresults = sorted(weekresults, key=lambda x: x['scores'], reverse=False)
    else:
        week_player_scores_list = []
        for x in result_list:
            if len(x.get("players", [])[0].get("holes", [])) == 9:
                for player in x.get('players', {}):
                    week_player_scores_list.append({
                        'team': x.get('team'),
                        'player': player.get('name'),
                        'scores': player.get('scores')})
        weekresults = sorted(week_player_scores_list, key=lambda x: x['scores'], reverse=False)
    return {'day': [], 'week': weekresults}


# TODO: Document Results
@app.post("/{course}/results", tags=["Other"])
async def update_results(team: Team, course: Course):
    team, = basemodels_to_dicts(team)
    team["scores"] = calculate_team_score(team["players"])
    holes_complete = len(team.get("players", [])[0].get("holes", []))
    if holes_complete == 9:
        new_team_data = db.update_document(course, team["id"], players=team["players"], scores=team["scores"], pin="")
    else:
        new_team_data = db.update_document(course, team["id"], players=team["players"], scores=team["scores"])
    return new_team_data


# TODO: Build endpoint
@app.get("/alarms", tags=["Other"])
async def get_alarms():
    alarms = db.get_collection("alarms")
    return alarms


# TODO: Build endpoint
@app.post("/alarm", tags=["Other"])
async def create_alarm(alarm: Alarm):
    alarm, = basemodels_to_dicts(alarm)
    alarm["id"] = str(alarm["hole"])
    db.upsert_document("alarms", alarm["course"] + alarm["id"], False, **alarm)
    return alarm


# TODO: Build endpoint
@app.post("/alarm/delete", tags=["Other"])
async def delete_alarm(alarm: Alarm):
    alarm, = basemodels_to_dicts(alarm)
    alarm["id"] = str(alarm["hole"])
    db.delete_document("alarms", alarm["course"] + alarm["id"], False)
    return alarm


# Test Data
'''f = open("./tests/new_team.json", "r")
new_team_tests_text = f.read()
f.close()
new_team_tests = json.loads(new_team_tests_text)'''
