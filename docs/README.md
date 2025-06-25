# PBF Comics AI Benchmark

This repository contains the static leaderboard webpage and the source code to generate and evaluate the PBF Comics Benchmark. The goal of this benchmark is to evaluate AI model visual understanding and comic explanation using a dataset of 285 comics from Nicholas Gurewitch's Perry Bible Fellowship comics (https://pbfcomics.com/).

## Updating the Leaderboard

To update the leaderboard with new benchmark results:

```bash
# Run new benchmark, updating models in models_config.yaml if needed
python run_benchmark.py
# Generate leaderboard static website
python generate_leaderboard.py

# Commit and push the updated leaderboard
git add docs/index.html
git commit -m "Update leaderboard with latest results"
git push
```