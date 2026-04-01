# 🎰 BetBot AI

AI-powered sports betting analytics and affiliate marketing bot.

## Features

- **AI Predictions** — ML model for NFL, NBA, MLB, NHL, Soccer
- **Odds Comparison** — compare lines across DraftKings, FanDuel, BetMGM, Caesars
- **Value Bets** — find edges where model probability exceeds market odds
- **Arbitrage Scanner** — detect risk-free arb opportunities across books
- **Bankroll Management** — Kelly criterion, unit betting, stop-loss protection
- **Affiliate Engine** — generate referral content for Twitter, Instagram, blogs
- **Export** — JSON/CSV output for all analytics

## Install

```bash
pip install -e .
```

## Commands

| Command | Description |
|---------|-------------|
| `betbot predict <sport>` | AI predictions for upcoming games |
| `betbot odds <sport>` | Compare odds across sportsbooks |
| `betbot value <sport>` | Find value bets (model vs market) |
| `betbot arbitrage <sport>` | Find arbitrage opportunities |
| `betbot bankroll` | View bankroll and ROI |
| `betbot bet <game> <side>` | Place a tracked bet |
| `betbot settle <index> <win/loss>` | Settle a pending bet |
| `betbot affiliate` | Manage affiliate links |
| `betbot content <sport>` | Generate social media posts with affiliate links |
| `betbot trends <team>` | Team trend analysis |
| `betbot dashboard` | Full terminal dashboard |
| `betbot export` | Export picks to JSON/CSV |

## Affiliate Setup

```bash
betbot affiliate --add DraftKings --url "https://draftkings.com/ref" --code "YOURCODE"
betbot affiliate --add FanDuel --url "https://fanduel.com/ref" --code "YOURCODE"
betbot content nba --platform twitter --book DraftKings
```

## Sports Supported

NFL · NBA · MLB · NHL · Soccer · NCAAF · NCAAB · MMA

## Disclaimer

For educational and entertainment purposes. Sports betting involves risk of financial loss. Please gamble responsibly. Past performance does not guarantee future results.
