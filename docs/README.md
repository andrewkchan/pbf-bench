# PBF Comics AI Benchmark - GitHub Pages Setup

This directory contains the static leaderboard webpage for the PBF Comics AI Benchmark.

## Setting up GitHub Pages

1. **Push this repository to GitHub**
2. **Enable GitHub Pages:**
   - Go to your repository settings
   - Navigate to the "Pages" section
   - Select "Deploy from a branch"
   - Choose "main" branch and "/docs" folder
   - Click "Save"

3. **Access your leaderboard:**
   - Your leaderboard will be available at: `https://yourusername.github.io/pbf-bench/`

## Updating the Leaderboard

To update the leaderboard with new benchmark results:

```bash
# After running a new benchmark
python generate_leaderboard.py

# Commit and push the updated leaderboard
git add docs/index.html
git commit -m "Update leaderboard with latest results"
git push
```

The GitHub Pages site will automatically update within a few minutes.

## Files

- `index.html` - The main leaderboard webpage
- `README.md` - This setup guide

## Customization

You can customize the leaderboard by:

1. Editing the `generate_leaderboard.py` script to modify the styling or layout
2. Updating the GitHub repository URL in the footer links
3. Adding additional information or sections to the methodology