# Phase 1: Ground Truth Labeling

This phase generates AI explanations for all PBF comics and provides a web interface for human labeling.

## Quick Start

1. **Setup**: Run the setup script to install dependencies and validate configuration:
   ```bash
   python3 setup_phase1.py
   ```

2. **Configure API Keys**: Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Generate AI Explanations**: Run the explanation generator:
   ```bash
   python3 generate_explanations.py
   ```

4. **Label Ground Truth**: Start the web app for manual labeling:
   ```bash
   python3 labeling_app.py
   ```
   Then open http://127.0.0.1:5000 in your browser.

## Components

### Configuration (`models_config.yaml`)
- Defines which models to use for explanation generation
- Configure API settings, rate limits, and prompts
- Default models: Claude 3.5 Sonnet, Gemini 2.0 Flash, GPT-4o

### Model Runner (`model_runner.py`)
- Unified interface for multiple AI providers (Anthropic, Google, OpenAI)
- Handles rate limiting, retries, and error handling
- Supports parallel processing of multiple models

### Explanation Generator (`generate_explanations.py`)
- Processes all comics with configured AI models
- Saves results to `ai_explanations.json`
- Supports resuming interrupted runs
- Options:
  ```bash
  python3 generate_explanations.py --help
  python3 generate_explanations.py --limit 10    # Process only first 10 comics
  python3 generate_explanations.py --stats       # Show statistics
  ```

### Labeling Web App (`labeling_app.py`)
- Simple web interface for reviewing AI explanations
- Side-by-side comparison of all model outputs
- Option to write custom explanations
- Keyboard shortcuts for efficiency (Ctrl+1/2/3, Ctrl+Enter)
- Progress tracking and auto-save

## Output Files

- `ai_explanations.json`: Raw AI explanations from all models
- `ground_truth_labels.json`: Human-selected best explanations

## API Costs

Generating explanations for all ~285 comics will cost approximately:
- Claude: ~$15-25
- GPT-4o: ~$10-20  
- Gemini: ~$5-10

Total estimated cost: ~$30-55

## Tips for Labeling

1. **Quality over Speed**: Take time to read all explanations carefully
2. **Look for Accuracy**: Does the explanation correctly identify what's happening?
3. **Check Completeness**: Does it cover all panels and the main joke/message?
4. **Prefer Clarity**: Choose explanations that are well-written and clear
5. **Use Custom**: Write your own if none of the AI explanations are good enough
6. **Keyboard Shortcuts**: Use Ctrl+1/2/3 to quickly select, Ctrl+Enter to submit

## Troubleshooting

### Common Issues

1. **API Key Errors**: Make sure all API keys are correctly set in `.env`
2. **Rate Limiting**: The system automatically handles rate limits, but you may see delays
3. **Large Images**: Some comics may be too large for certain APIs (will be logged as errors)
4. **Network Issues**: Failed requests are automatically retried up to 3 times

### Recovery

- The explanation generator can be interrupted and resumed
- The labeling app auto-saves progress
- All data is stored in JSON files for easy backup/recovery

## Next Steps

After completing Phase 1, you'll have:
- `ground_truth_labels.json` with human-validated explanations
- Ready to proceed to Phase 2: Benchmark Runner