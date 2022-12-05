export interface IRecord {
    id: string;
    name: string;
}

export enum IMessageColor {
    GOOD = 'good',
    WARNING = 'warning',
    DANGER = 'danger'
}

export interface IMessage {
    channel: string;
    title: string;
    link: string;
    color: IMessageColor,
    fields: {
        jira_ticket: string;
        pr_name: string;
    }
}
