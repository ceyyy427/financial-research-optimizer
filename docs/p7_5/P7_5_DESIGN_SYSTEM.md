# P7.5 design system

The local shell uses a restrained research-notebook visual language: warm
off-white background, white evidence cards, charcoal text, and one teal link
colour. It avoids gradients, trading-dashboard hype, scores, and leaderboard
colour coding.

## Tokens

| Token | Value | Use |
| --- | --- | --- |
| ink | `#182026` | Body and evidence text |
| paper | `#f7f7f2` | Page background |
| surface | `#ffffff` | Cards and panels |
| line | `#d8dfdb` | Boundaries |
| link | `#095a66` | Links and focus-adjacent affordances |
| radius | `10px` | Cards |
| measure | `980px` | Readable page width |

Typography is system UI with normal weight contrast and short line lengths.
Semantic headings define the page hierarchy. Badges are reserved for state
labels such as `CAPTURED`, `SAMPLE`, `OFFLINE`, and `PRIVATE BY DEFAULT`; they
never imply performance or confidence.

## Interaction contract

Primary actions are inspect, explain, run a bounded experiment, save privately,
and reopen. Destructive, external, or financial actions are absent. An error
must say what failed, whether data was saved, and the next safe action.
