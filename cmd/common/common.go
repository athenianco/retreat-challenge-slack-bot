package common

type Message struct {
	Channel string `json:"channel"`
	Title   string `json:"title"`
	Text    string `json:"text"`
	Link    string `json:"link,omitempty"`
	// good (green), warning (yellow), danger (red), or any hex color code (eg. #439FE0)
	Color  string            `json:"color"`
	Fields map[string]string `json:"fields"`
}
