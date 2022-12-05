import { writeFileSync } from 'fs';
import axios from 'axios';
import * as moment from 'moment';
import { IMessage, IMessageColor, IRecord } from './types';

class Test {
    private hoursLimit = 1
    private params = {
        account: 1,
        date_from: moment().subtract(3,'d').format('YYYY-MM-DD'),
        date_to: moment().format('YYYY-MM-DD'),
        in: [
            "github.com/athenianco/athenian-webapp"
        ],
        stages: [
            "wip"
        ],
        exclude_inactive: true
    }
    private headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + process.env.ATHENIAN_TOKEN
    }

    constructor() {
        this.generateJson();
    }

    private async generateJson(): Promise<void> {
        const filteredPRs = await this.assignFilteredPRs();
        filteredPRs.forEach((pr) => {
            const obj: IMessage = {
                channel: "retreat-2022-challenge-slack-bot-test",
                title: `PR review time is more than ${this.hoursLimit} hours`,
                link: "https://cutt.ly/A1it7td",
                color: IMessageColor.DANGER,
                fields: {
                    jira_ticket: pr.id,
                    pr_name: pr.name,
                }
            }
            writeFileSync("message.json", JSON.stringify(obj));
        });
    }

    private async assignFilteredPRs(): Promise<IRecord[]> {
        const response = await this.getPRList();
        return response.data
            .filter((pr) => {
                const curDate = moment();
                const prCreated = moment(pr.created);
                const durationCurDate = moment.duration(curDate.diff(prCreated)).asHours();
                if (durationCurDate < this.hoursLimit) return false
                const prFirstReview = moment(pr.first_review);
                const durationFirstReview = moment.duration(prFirstReview.diff(prCreated)).asHours();
                return durationFirstReview >= this.hoursLimit;
            }).map((pr) => {
                return {
                    id: pr?.jira[0]?.id || null,
                    name: pr?.jira[0]?.title || null,
                }
            });
    }

    private async getPRList(): Promise<any> {
        return new Promise(async (resolve, reject) => {
            try {
                const resp = await axios.post('https://api.athenian.co/v1/filter/pull_requests', this.params, { headers: this.headers });
                resolve(resp.data);
            } catch (err) {
                throw new Error(err.toString());
            }
        })
    }
}

new Test();
