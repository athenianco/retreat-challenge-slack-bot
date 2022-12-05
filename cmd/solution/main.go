package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/athenianco/retreat-challenge-slack-bot/cmd/common"
)

var (
	command = flag.String("c", "default command", "slack command")
)

type user struct {
	Login    string `json:"login"`
	NativeID string `json:"native_id"`
}

type Includes struct {
	Include Include `json:"include"`
}

type Include struct {
	Jira map[string]Jira `json:"jira"`
}

type Jira struct {
	ID     string   `json:"id"`
	Labels []string `json:"labels"`
	Type   string   `json:"type"`
}

func main() {
	flag.Parse()
	if err := run(); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	issues, err := fetchIssues()
	if err != nil {
		return err
	}
	msg, err := postProcess(issues)
	if err != nil {
		return err
	}

	data, err := json.MarshalIndent(msg, "", "\t")
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}

func fetchIssues() (map[string]Jira, error) {
	req, err := http.NewRequest("POST", "https://api.athenian.co/v1/filter/deployments", strings.NewReader(reqBodyFormat))
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

	var includes Includes
	if err := json.Unmarshal(data, &includes); err != nil {
		return nil, err
	}
	return includes.Include.Jira, nil
}

func postProcess(issues map[string]Jira) (*common.Message, error) {
	count := len(issues)
	types := make(map[string]int)
	labels := make(map[string]int)
	var labelsCount int
	for _, i := range issues {
		_, ok := types[i.Type]
		if !ok {
			types[i.Type] = 1
		} else {
			types[i.Type]++
		}
		for _, l := range i.Labels {
			labelsCount++
			_, ok := labels[l]
			if !ok {
				labels[l] = 1
			} else {
				labels[l]++
			}
		}
	}
	slackLabels := make(map[string]string)
	for k, v := range types {
		slackLabels[fmt.Sprintf(":jira: _%s_ %d(%d%%)", k, v, 100*v/count)] = ""
	}
	for k, v := range labels {
		slackLabels[fmt.Sprintf(":label: _%s_ %d(%d%%)", k, v, 100*v/labelsCount)] = ""
	}

	return &common.Message{
		Channel: "retreat-hackathon",
		Title:   fmt.Sprintf("%d JIRA issues deployed last sprint", count),
		Text:    "Breakdown of `athenian-webapp` team's JIRA issues deployed last sprint:",
		Link:    "https://app.athenian.co/analytics/compare/teams/table",
		Color:   "good",
		Fields:  slackLabels,
	}, nil
}

const (
	reqBodyFormat = `{
  "account": 1,
  "date_from": "2022-10-14",
  "date_to": "2022-10-31",
  "in": [
    "github.com/athenianco/athenian-webapp"
  ],
  "environments": [
    "production"
  ],
  "conclusions": [
    "SUCCESS"
  ],
  "with": {
    "pr_author": [
      "github.com/akbarik",
      "github.com/alex-athenian",
      "github.com/baristna",
      "github.com/znegrin"
    ]
  }
}
`
)
