import { writeFileSync } from 'fs';
import axios from "axios";
import * as moment from "moment";

class Test {
    private hoursLimit = 10
    private params = {
        account: 1,
        date_from: "2022-11-28",
        date_to: "2022-11-30",
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
        'Authorization': 'Bearer ' + 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1FTkNPVVl6UVRZeVFqTXhSVVF5TVRGR04wWkNNVUV5UXpCR05rUTJPVEF6TnpRMlJUUXdPQSJ9.eyJpc3MiOiJodHRwczovL2F0aGVuaWFuLXByb2R1Y3Rpb24uYXV0aDAuY29tLyIsInN1YiI6ImdpdGh1Ynw5OTE4MjY5OCIsImF1ZCI6WyJodHRwczovL2FwaS5hdGhlbmlhbi5jbyIsImh0dHBzOi8vYXRoZW5pYW4tcHJvZHVjdGlvbi5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNjY5ODA1NTY0LCJleHAiOjE2Njk4OTE5NjQsImF6cCI6Im1JNTlRaGdSYzdlM0RHVUpkdVdDRFd3eW5HVWxIYm9QIiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCJ9.l08B_C9TJMEIIq4deT9Q_qY0EJoPj23LgNKyk8Q0dYUn41JG_1t2U1-Odz2gKQgNv55jEzbrYBh68Dx5f4OcKfnIPt6FUrYML6bUOZIg_kjaFiCK3LA_gwFAfhCyRM7T6P67DkrBsoFAdG_ct0Rsi-in6vKk47RfDCs5vJ-8txBr12mS9XS5v-QcShqtqb9y78MnXPTdK_zMsWtZpm5nYZ-RSqZ_FYkolvrQks2w908WIB5b3VXCctbVTavZCAUWYWk9A3UQYOdx1UCT0dG2sxYv2THit_KZP9WKH9hbmoxAQ4szDbHgPc2uChO57dFTXn0rwp3hYuLjrNzEK7oK1Q'
    }

    constructor() {
        this.generateJson();
    }

    private async generateJson(): Promise<void> {
        const filteredPRs = await this.assignFilteredPRs();
        filteredPRs.forEach((pr) => {
            const obj = {
                channel: "retreat-2022-challenge-slack-bot-test",
                title: `PR review time is more than ${this.hoursLimit} hours`,
                color: "danger",
                fields: {
                    jira_ticket: pr.id,
                    pr_name: pr.name,
                }
            }
            writeFileSync("message-example.json", JSON.stringify(obj));
        });
    }

    private async assignFilteredPRs(): Promise<any> {
        const response = await this.getPRList();
        return response.data
            .filter((pr) => {
                if (!pr?.created || !pr?.first_review) return false;
                const prCreated = moment(pr.created);
                const prFirstReview = moment(pr.first_review);
                const duration = moment.duration(prFirstReview.diff(prCreated));
                const hours = duration.asHours();
                return hours >= this.hoursLimit;
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
                const resp = await axios.post('https://api.athenian.co/v1/filter/pull_requests', this.params, {headers: this.headers});
                resolve(resp.data);
            } catch (err) {
                console.error(err);
            }
        })
    }
}

new Test();
