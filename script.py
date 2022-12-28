import json
import requests
from datetime import datetime, timedelta
from humanize.time import precisedelta

TOKEN = ''
SLACK_TOKEN = ''

# python script.py && ./publish.sh $(pwd)/message.json xoxb-825794908018-4409413555383-oRP9K5mL4V9JQQx5iBapTUFb
base_url = 'https://api.athenian.co'


'''
TODOs:
- extend to other metrics
- alerting on the "pendings"
'''

headers = {
    'Authorization': f'Bearer {str(TOKEN)}',
    'Content-Type': 'application/json'
}

metrics_mapping = {
    # 'pr-reviewed-ratio': {
    #     'better': 'higher',
    #     'granularity': 'multi'
    # },
    'pr-review-time': {
        'better': 'lower',
        'granularity': 'single'
    },
    # 'jira-lead-time': {
    #     'better': 'lower',
    #     'granularity': 'single'
    # },
}

def do_request(path, method, data=None):
    if method.upper() == 'POST':
        return requests.post(f'{base_url}{path}', data=json.dumps(data), headers=headers)
    else:
        return requests.get(f'{base_url}{path}', headers=headers)


def fetch_goals():
    print('Fetching goals...')
    goals_data = do_request('/private/align/goals', 'POST', {
        'account': 1,
        'team': 0,
        'only_with_targets': True
    })
    goals = goals_data.json()
    print(f'{len(goals)} goals fetched')
    active_goals = [
        g for g in goals
        if datetime.strptime(g['valid_from'], '%Y-%m-%d') <= datetime.today() < datetime.strptime(g['expires_at'], '%Y-%m-%d')
    ]

    print(f'{len(active_goals)} active goals found')
    return active_goals


def identify_risky_prs_for_goal(goal):
    print(f'Identifying risky PRs for goal {goal["name"]}...')
    if metrics_mapping.get(goal['metric']) is None:
        risky_prs = {}
    else:
        print(json.dumps(goal, indent=4))
        risky_prs = identify_risky_prs_for_team_goal(goal['team_goal'], goal['metric'])

    # print(risky_prs)
    # print(f'{len(risky_prs)} risky PRs identified')
    return risky_prs


def identify_risky_prs_for_team_goal(team_goal, metric):
    all_prs = {}
    current = team_goal['value']['current']
    target = team_goal['value'].get('target')

    filtered_prs = []
    if target is not None:
        target = float(target)
        prs = fetch_prs(team_goal['team']['id'], team_goal['team']['name'], goal['valid_from'], None)
        filtered_prs = []
        for pr in prs:
            review_timing = pr['stage_timings'].get('review')
            if review_timing is not None:
                value = int(review_timing[:-1])
                if value > target:
                    filtered_prs.append(pr)

        print(target, filtered_prs[0]['stage_timings']['review'])

        # if metrics_mapping[metric]['better'] == 'higher':
        #     if current < target:
        #         print('Below target value')
        #         # TODO: filter PRs
        #         prs = fetch_prs(team_goal['team']['id'], goal['valid_from'], None)
        # else:
        #     if current > target:
        #         print('Above target value')

    all_prs[team_goal['team']['name']] = filtered_prs
    children = team_goal.get('children', [])
    for c in children:
        all_prs.update(identify_risky_prs_for_team_goal(c, metric))

    return all_prs


def fetch_prs(team_id, team_name, starting_date, condition):
    print(f'Fetching members for team {team_id} [{team_name}]...')
    members_data = do_request(f'/private/align/members/{team_id}/?recursive=true&account=1', 'GET')
    members = members_data.json()
    print(f'{len(members)} members fetched')

    logins = [m['login'] for m in members]

    print('Fetching PRs...')

    prs_data = do_request('/v1/filter/pull_requests', 'POST', {
        'account': 1,
        'date_from': starting_date,
        'date_to': datetime.today().strftime('%Y-%m-%d'),
        # 'jira': {}, TODO: based on goal filter
        'in': ['{84}'], # TODO: based on goal filter
        'stages': ['wip', 'reviewing', 'merging', 'releasing', 'done'],
        'with': {
            'author': logins,
        },
        'exclude_inactive': True,
    })
    prs = prs_data.json()['data']
    print(f'{len(prs)} PRs fetched')
    return prs


if __name__ == '__main__':
    goals = fetch_goals()

    for goal in goals:
        risky_prs = identify_risky_prs_for_goal(goal)
        if risky_prs:
            top_prs_by_team = {}
            for team, prs in risky_prs.items():
                top_prs = sorted(prs, key=lambda pr: int(pr['stage_timings']['review'][:-1]),
                                 reverse=True)[:5]
                top_prs_formatted = []
                for pr in top_prs:
                    delta = timedelta(seconds=int(pr['stage_timings']['review'][:-1]))
                    human_delta = precisedelta(delta, minimum_unit='minutes', suppress=['months'], format='%0.0f')
                    top_prs_formatted.append(
                        f'- [*{human_delta}*] <{pr["repository"]}/pull/{pr["number"]}|{pr["title"]}>'
                    )

                top_prs_by_team[team] = '\n'.join(top_prs_formatted)

            msg = {
                "channel": "retreat-2022-challenge-slack-bot-test",
                "title": "Worst PRs for goals",
                "text": "Worst PRs for goal: 'Reduce code review time'",
                "color": "danger",
                "fields": top_prs_by_team
            }

            with open('message.json', 'w') as fout:
                json.dump(msg, fout, indent=4)
