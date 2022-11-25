package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"github.com/athenianco/retreat-challenge-slack-bot/cmd/common"
	"github.com/slack-go/slack"
	"os"
)

var (
	messagePath = flag.String("f", "/etc/message.json", "path to the slack message json file")
)

func main() {
	flag.Parse()
	if err := run(); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	data, err := os.ReadFile(*messagePath)
	if err != nil {
		return err
	}
	var msg common.Message
	if err := json.Unmarshal(data, &msg); err != nil {
		return err
	}
	token := os.Getenv("SLACK_TOKEN")
	if token == "" {
		return errors.New("SLACK_TOKEN must be specified")
	}
	cli := slack.New(token)
	return sendMessage(cli, msg)
}

func sendMessage(c *slack.Client, m common.Message) error {
	if m.Channel == "" {
		return errors.New("channel name must be set")
	}
	var fields []slack.AttachmentField
	for k, v := range m.Fields {
		fields = append(fields, slack.AttachmentField{
			Title: k,
			Value: v,
		})
	}
	_, _, _, err := c.SendMessage(m.Channel, slack.MsgOptionAttachments(slack.Attachment{
		Title:      m.Title,
		TitleLink:  m.Link,
		Text:       m.Text,
		Color:      m.Color,
		Fields:     fields,
		MarkdownIn: []string{"text"},
	}))
	fmt.Println("the message was successfully sent")
	return err
}
