#!/usr/bin/env python3

import dataclasses
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import graphviz
import requests
import slack_bolt
from slack_bolt.adapter.socket_mode import SocketModeHandler

_ACCOUNT = 1
_REPOSET = 7
_HOST = "https://api-staging.athenian.co"
_IGNORE_TEAMS = [
    "Athenian",
    'Apps',
    "Bots",
    "Dashboard",
    "Engineering",
    "Test Team",
    "Test Team for caching issues",
]

_now = datetime.now(tz=timezone.utc)


CHANNEL = "retreat-2022-challenge-gaetano"
CHANNEL = "retreat-2022-challenge-slack-bot-test"

_out = {
    "channel": CHANNEL,
    "title": "Across team boundaries PRs",
    "text": "foo bar2",
    "link": "https://cutt.ly/A1it7td",
    "color": "good",
    "fields": {
        # "luck": "10%",
        # "skill": "20%",
        # "concentrated power of will": "15%",
        # "pleasure": "5%",
        # "pain": "50%",
    },
}


def get_prs(delta: timedelta, use_cache: bool = True):
    _CACHE = "/tmp/prs.json"

    if use_cache and os.path.exists(_CACHE):
        with open(_CACHE, "r") as fp:
            return json.load(fp)

    url = f"{_HOST}/v1/filter/pull_requests"
    from_ = (_now - delta).date().isoformat()
    to_ = _now.date().isoformat()
    body = {
        "account": _ACCOUNT,
        "date_from": "2022-11-01",
        "date_to": "2022-12-31",
        "exclude_inactive": True,
        "stages": ["wip", "reviewing", "merging", "releasing", "done"],
        "in": [f"{{{_REPOSET}}}"],
    }

    res = requests.post(url, json=body)
    with open(_CACHE, "w") as fp:
        json.dump(res.json()["data"], fp)

    return res.json()["data"]


def get_member_teams(use_cache: bool = True):
    _CACHE = "/tmp/members_teams.json"

    if use_cache and os.path.exists(_CACHE):
        with open(_CACHE, "r") as fp:
            return json.load(fp)

    url = f"{_HOST}/v1/teams/{_ACCOUNT}"
    res = requests.get(url)
    members = {}
    for team in res.json():
        for member in team.get("members", ()):
            if member["login"] not in members:
                members[member["login"]] = []
            if team["name"] not in _IGNORE_TEAMS:
                members[member["login"]].append(team["name"])

    with open(_CACHE, "w") as fp:
        json.dump(members, fp)
    return members


@dataclasses.dataclass
class _RepoPRs:
    repo: str
    across_border: list[dict]
    within_border: list[dict]


def filter_prs(prs: list[dict], member_teams: dict) -> list[_RepoPRs]:
    res = []
    _repos_prs = dict()

    for pr in prs:
        if pr["repository"] not in _repos_prs:
            _repos_prs[pr["repository"]] = _RepoPRs(pr["repository"], [], [])

        repo_prs = _repos_prs[pr["repository"]]

        parts = pr.get("participants", [])
        author_part = next((part for part in parts if "author" in part["status"]), None)
        if not author_part:
            repo_prs.within_border.append(pr)
            continue

        author_id = author_part["id"]
        author_teams = member_teams.get(author_id, [])

        if not author_teams:
            repo_prs.within_border.append(pr)
            continue

        participants = [part for part in parts]

        across_border = False
        for part in participants:
            if set(part.get("status", ())) & {"merger", "reviewer", "commenter"}:
                if part["id"] == author_id:
                    continue

                part_id_teams = member_teams.get(part["id"], [])
                if not part_id_teams:
                    continue

                if not (set(part_id_teams) & set(author_teams)):
                    across_border = True
                    break
        if across_border:
            repo_prs.across_border.append(pr)
        else:
            repo_prs.within_border.append(pr)

    return _repos_prs.values()


def print_result(repos_prs: list[_RepoPRs], members_teams: dict):
    out = []
    graph = graphviz.Digraph("across teams contributors", format="png")
    graph_teams = graphviz.Digraph("across teams", format="png")
    edges = defaultdict(lambda: 0)
    edges_teams = defaultdict(lambda: 0)

    for repo_prs in repos_prs:
        ratio = len(repo_prs.across_border) / (
            len(repo_prs.within_border) + len(repo_prs.across_border)
        )
        if not ratio:
            continue
        out.append(f"*Repository* {repo_prs.repo}")
        # out.append("PRs across team border: %.4f" % ratio * 100)
        out.append("PRs across team boundaries: %.2f%%" % (ratio * 100,))
        for pr in repo_prs.across_border:
            author_part = next(
                (part for part in pr.get("participants", ()) if "author" in part["status"]), None,
            )
            assert author_part
            author_id = author_part["id"]
            author_teams = members_teams.get(author_id, [])
            across_parts = []
            auth = author_id.split("/")[-1]

            for part in pr.get("participants"):
                if set(part.get("status", ())) & {"merger", "reviewer", "commenter"}:
                    if part["id"] == author_id:
                        continue

                    part_id_teams = members_teams.get(part["id"], [])
                    if not part_id_teams:
                        continue

                    if not (set(part_id_teams) & set(author_teams)):
                        across_parts.append(part["id"])
                        part_id = part["id"].split("/")[-1]
                        graph.node(auth)
                        graph.node(part_id)
                        edges[(auth, part_id)] += 1

                        graph_teams.node(author_teams[0])
                        graph_teams.node(part_id_teams[0])
                        edges_teams[(author_teams[0], part_id_teams[0])] += 1

            out.append(f"- _{pr['title']}_ author: {author_id} external participants {across_parts}")

    for edge, size in edges.items():
        graph.edge(*edge, penwidth=str(max(0.5, math.log2(size))))

    for edge, size in edges_teams.items():
        graph_teams.edge(
            *edge,
            penwidth=str(max(0.5, size / 5)),
        )

    # graph.render("/tmp/participants-graph", view=False)
    return "\n".join(out), graph, graph_teams


import os

app = slack_bolt.App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("SIGN_TOKEN"),
)


@app.message("teams-cohesion")
def handle_message(message, say):
    # say(os.getenv("SAY"))
    text, graph, graph_teams = _do()
    graph.render("/tmp/pr-graph", view=False)
    graph_teams.render("/tmp/pr-graph-teams", view=False)
    say(text)
    with open("/tmp/pr-graph.png", "rb") as fp:
        app.client.files_upload(
            file=fp.read(),
            title="Members graph",
            filename="members-graph.png",
            channels=[CHANNEL],
        )

    with open("/tmp/pr-graph-teams.png", "rb") as fp:
        app.client.files_upload(
            file=fp.read(),
            title="Teams graph",
            filename="teams-graph.png",
            channels=[CHANNEL],
        )



def _do():
    USE_CACHE = False
    prs = get_prs(timedelta(days=31), USE_CACHE)
    member_teams = get_member_teams(USE_CACHE)
    repos_prs = filter_prs(prs, member_teams)
    return print_result(repos_prs, member_teams)


def main():
    # USE_CACHE = True
    # prs = get_prs(timedelta(days=14), USE_CACHE)
    # member_teams = get_member_teams(USE_CACHE)
    # repos_prs = filter_prs(prs, member_teams)
    rr, graph = _do()
    _out["text"] = rr
    json.dump(_out, sys.stdout, indent=True)
    # print(rr)


if __name__ == "__main__":
    # main()
    SocketModeHandler(app, os.getenv("APP_TOKEN")).start()
