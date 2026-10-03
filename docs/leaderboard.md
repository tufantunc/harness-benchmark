# Leaderboard — glm-5.2

## Summary

| Rank | Harness | Served Model | Tasks | Success | pass@k | Tokens/Success | Cost/Task | Avg Time | Avg Requests |
|------|---------|--------------|-------|---------|--------|----------------|-----------|----------|--------------|
| 1 | dsh | glm-5.3 | 249 | 83.5% | 94.0% | 213,297 | $0.0000 | 156s | 13.3 |
| 2 | crush | glm-5.3 | 249 | 66.7% | 86.8% | 190,899 | $0.0000 | 143s | 12.7 |
| 3 | goose | glm-5.3 | 249 | 63.0% | 85.5% | 199,598 | $0.0000 | 204s | 12.4 |

## Cache & Overhead

| Harness | Cache Write | Cache Read | Sys Prompt | Tool Schemas | Prefix Stable |
|---------|-------------|------------|------------|--------------|---------------|
| dsh | 0 | 0 | 642 | 4,815 | 100% |
| crush | 0 | 0 | 5,471 | 6,195 | 94% |
| goose | 0 | 0 | 1,087 | 3,388 | 100% |
