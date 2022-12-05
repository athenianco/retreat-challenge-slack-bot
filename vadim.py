from datetime import date, timedelta
import io
import logging
import os

import matplotlib
matplotlib.use("agg")
from matplotlib import pyplot as plt
import numpy as np
import requests
from scipy.interpolate import interp1d
import slack_bolt
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.logger import get_bolt_logger

app = slack_bolt.App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("SIGN_TOKEN"),
)


@app.event("app_mention")
def event_test(say, body):
    metric, role, login = body["event"]["text"].split(" ")[1:]
    today = date.today()
    response = requests.post("https://api.athenian.co/v1/metrics/pull_requests", json={
        "account": 1,
        "metrics": [metric],
        "date_from": str(today - timedelta(days=60)),
        "date_to": str(today),
        "granularities": ["aligned week"],
        "exclude_inactive": True,
        "for": [{
            "repositories": ["{84}"],
            "with": {
                role: [f"github.com/{login}"],
            },
        }],
    }).json()
    dates = []
    values = []
    cmins = []
    cmaxs = []
    dtype = None
    for mv in response["calculated"][0]["values"]:
        if (value := mv["values"][0]) is not None:
            dates.append(date.fromisoformat(mv["date"]))
            if isinstance(value, str):
                values.append(timedelta(seconds=int(value[:-1])))
                cmins.append(timedelta(seconds=int(mv["confidence_mins"][0][:-1])))
                cmaxs.append(timedelta(seconds=int(mv["confidence_maxs"][0][:-1])))
                dtype = "timedelta64[s]"
            else:
                values.append(value)
                cmins.append(mv["confidence_mins"][0])
                cmaxs.append(mv["confidence_maxs"][0])
    dates = np.array(dates, dtype="datetime64[ns]")
    values = np.array(values, dtype=dtype)
    cmins = np.array(cmins, dtype=dtype)
    cmaxs = np.array(cmaxs, dtype=dtype)
    order = np.argsort(dates)
    dates = dates[order]
    values = values[order]
    cmins = cmins[order]
    cmaxs = cmaxs[order]
    if dtype == "timedelta64[s]":
        values = values.view(int)
        cmins = cmins.view(int)
        cmaxs = cmaxs.view(int)
    dates_smooth = np.linspace(dates.min().view(int), dates.max().view(int), 300).astype(int)
    interp_kind = "quadratic"
    plt.plot(
        dates_smooth.view("datetime64[ns]"),
        interp1d(dates.view(int), values, kind=interp_kind)(dates_smooth),
    )
    plt.fill_between(
        dates_smooth.view("datetime64[ns]"),
        interp1d(dates.view(int), cmins, kind=interp_kind)(dates_smooth),
        interp1d(dates.view(int), cmaxs, kind=interp_kind)(dates_smooth),
        alpha=0.25,
    )
    plt.scatter(dates, values)
    if dtype == "timedelta64[s]":
        plt.gca().yaxis.set_major_formatter(lambda x, _: str(timedelta(seconds=int(x))))
    plt.gca().set_ylim(ymin=0)
    plt.gca().set_xticks(dates)
    plt.gca().set_yticks(values)
    plt.xticks(rotation=45, ha="right")
    plt.gca().grid(axis="y", linestyle="dotted", alpha=0.75)
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    # plt.savefig("tmp.png", format="png", bbox_inches="tight", dpi=150)
    plt.clf()
    app.client.files_upload(
        file=buffer.getvalue(),
        title=" ".join([metric, role, login]),
        filename="-".join([metric, role, login]) + ".png",
        channels=body["event"]["channel"],
    )


if __name__ == "__main__":
    get_bolt_logger(slack_bolt.App).level = logging.ERROR
    SocketModeHandler(app, os.getenv("APP_TOKEN")).start()
