package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"

	"github.com/athenianco/retreat-challenge-slack-bot/cmd/common"
)

var (
	command = flag.String("c", "default command", "slack command")
)

type user struct {
	Login    string `json:"login"`
	NativeID string `json:"native_id"`
}

func main() {
	flag.Parse()
	if err := run(); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	var msg common.Message
	if *command != "who are you" {
		msg = common.Message{
			Channel: "retreat-2022-challenge-slack-bot-test",
			Title:   "Command 404",
			Text:    "Dunno such command",
			Color:   "warning",
			Fields: map[string]string{
				"command": *command,
			},
		}
	} else {
		u, err := fetchUser()
		if err != nil {
			return err
		}
		msg = common.Message{
			Channel: "retreat-2022-challenge-slack-bot-test",
			Title:   "Yo " + u.Login,
			Text:    *command,
			Link:    "https://cutt.ly/A1it7td",
			Color:   "good",
			Fields: map[string]string{
				"id": u.NativeID,
			},
		}
	}
	data, err := json.MarshalIndent(msg, "", "\t")
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}

func fetchUser() (*user, error) {
	req, err := http.NewRequest("GET", "https://api.athenian.co/v1/user", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Add("accept", "application/json")
	req.Header.Add("Authorization", "Bearer "+os.Getenv("BEARER"))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var u user
	if err := json.Unmarshal(data, &u); err != nil {
		return nil, err
	}
	return &u, nil
}
