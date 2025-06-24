# Phase 2: Benchmark Runner

This phase runs AI models on the PBF comics dataset and scores their explanations against ground truth using a judge AI.

## Prerequisites

- Completed Phase 1 (have `ground_truth_labels.json` file)
- AI explanations generated (`ai_explanations.json`)
- API keys configured in `.env`

## Quick Start

```bash
# Activate virtual environment
source env/bin/activate

# Run benchmark on a small subset first (recommended)
python3 run_benchmark.py --limit 5

# Run full benchmark on all comics with ground truth
python3 run_benchmark.py

# Test specific models only
python3 run_benchmark.py --models claude-3-5-sonnet gpt-4o

# Test specific comics
python3 run_benchmark.py --comics PBF-Bright.png PBF-Brushed.png
```

## Components

### Judge System (`judge.py`)
- Uses a strong AI model (default: Claude 3 Opus) to score explanations
- Compares model outputs against ground truth explanations  
- Scores on 4 criteria: Accuracy, Completeness, Insight, Clarity
- Returns structured scores with detailed reasoning

### Benchmark Runner (`run_benchmark.py`)
- Runs any combination of models on the comic dataset
- Uses the same `model_runner.py` infrastructure as Phase 1
- Generates explanations and scores them using the judge
- Outputs results in both CSV and detailed JSON formats

## Configuration

Models and settings are configured in `models_config.yaml`:

```yaml
# Models to evaluate in the benchmark
benchmark_models: [claude-3-opus, claude-3-5-sonnet, gemini-2.0-flash, gpt-4o, gpt-4o-mini]

# Model to use as judge (should be a strong model)
judge_model: claude-3-opus
```

## Scoring Criteria

The judge evaluates explanations on a 1-10 scale across 4 dimensions:

1. **Accuracy (40% weight)**: Does the explanation correctly identify what's happening?
2. **Completeness (25% weight)**: Does it cover all important visual elements and story beats?
3. **Insight (25% weight)**: Does it understand and explain the humor, irony, or message?
4. **Clarity (10% weight)**: Is the explanation well-written and easy to understand?

**Overall Score** = (Accuracy × 0.4) + (Completeness × 0.25) + (Insight × 0.25) + (Clarity × 0.1)

## Output Files

### CSV Results (`benchmark_results.csv`)
- One row per model with summary statistics
- Columns: model name, version, per-comic scores, average/median/min/max
- Ready for analysis and visualization

### Detailed JSON (`benchmark_details.json`)
- Complete results including all explanations and judge reasoning
- Metadata about the benchmark run
- Full scoring breakdown for each comic and model

## Example Usage

```bash
# Quick test with 3 models on 10 comics
python3 run_benchmark.py --models claude-3-5-sonnet gpt-4o gemini-2.0-flash --limit 10

# Full benchmark with custom output files
python3 run_benchmark.py --output-csv results_v1.csv --output-json details_v1.json

# Test only specific comics that were challenging
python3 run_benchmark.py --comics PBF-Bright.png PBF-Brushed.png PBF-Pop.png
```

## Expected Costs

Running the full benchmark (~285 comics) with 5 models + judge:
- **Model Evaluation**: ~$150-200 (5 models × 285 comics × ~$0.10-0.15 per comic)
- **Judge Scoring**: ~$75-100 (1 judge × 5 models × 285 comics × ~$0.05 per score)
- **Total**: ~$225-300

Cost per comic varies by model:
- Claude: ~$0.15-0.20
- GPT-4o: ~$0.10-0.15  
- Gemini: ~$0.05-0.10

## Performance Optimization

- **Parallel Processing**: Models run concurrently for each comic
- **Rate Limiting**: Automatic rate limiting to respect API limits
- **Resumability**: Can be interrupted and resumed (though not implemented yet)
- **Batch Processing**: Processes comics in batches to manage memory

## Troubleshooting

### Common Issues

1. **"No ground truth found"**: Make sure you've completed Phase 1 and have `ground_truth_labels.json`
2. **Judge errors**: Check that the judge model (default: Claude 3 Opus) is properly configured
3. **Rate limiting**: The system handles this automatically, but very aggressive usage may hit limits
4. **Memory usage**: Large numbers of comics may use significant memory

### Debugging

```bash
# Test the judge system independently
python3 judge.py

# Check if ground truth and AI explanations are properly linked
python3 -c "
import json
with open('ground_truth_labels.json') as f: gt = json.load(f)
with open('ai_explanations.json') as f: ai = json.load(f)
print(f'Ground truth: {len(gt)} comics')
print(f'AI explanations: {len(ai)} comics')
print(f'Overlap: {len(set(gt.keys()) & set(ai.keys()))} comics')
"
```

## Next Steps

After completing the benchmark:
- Review results in `benchmark_results.csv`  
- Analyze detailed judge reasoning in `benchmark_details.json`
- Proceed to Phase 3: Generate leaderboard webpage