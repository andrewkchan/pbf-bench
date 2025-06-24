# PBF Comics Benchmark Plan

## Overview
Create a benchmark for evaluating AI models on comic explanation tasks using the PBF Comics dataset.

## Phase 1: Ground Truth Labeling System

### Components
1. **API Integration Script** (`generate_explanations.py`)
   - Run configurable set of models (default: Claude, Gemini 2.5, GPT-4o)
   - Uses same model configuration system as Phase 2
   - Handle rate limiting and retries
   - Save all responses for review

2. **Labeling Web App** (`labeling_app.py`)
   - Simple UI to review explanations and select/edit the best one
   - Side-by-side comparison of all 3 AI explanations
   - Ability to write custom explanation if none are satisfactory
   - Progress tracking and ability to skip/return to comics

3. **Data Storage**
   - Input: `pbf_comics_metadata.json` (from download script)
   - Output: `ground_truth_labels.json` with selected explanations
   - Intermediate: `ai_explanations.json` with all 3 model outputs

### Key Decisions
- **API Keys**: Store in `.env` file (already in `.gitignore`)
- **Batch Processing**: Process comics in batches of 10 to handle API rate limits
- **Web Framework**: Simple Flask app with SQLite for session persistence
- **UI Features**: 
  - Side-by-side comparison view
  - Radio buttons to select best explanation
  - Text area for custom explanation
  - Progress bar showing completion status
  - Keyboard shortcuts for efficiency

### Data Format
```json
{
  "comic_id": {
    "image_path": "path/to/image.png",
    "comic_title": "Title",
    "explanations": {
      "claude": "Claude's explanation...",
      "gemini": "Gemini's explanation...",
      "gpt4o": "GPT-4o's explanation..."
    },
    "selected": "claude|gemini|gpt4o|custom",
    "custom_explanation": "Optional custom explanation...",
    "labeled_by": "human",
    "labeled_at": "timestamp"
  }
}
```

## Phase 2: Benchmark Runner

### Components
1. **Model Runner** (`run_benchmark.py`)
   - Configurable to run any list of AI models
   - Parallel processing where possible
   - Progress tracking and resumability

2. **Judge System** (`judge.py`)
   - Use Claude as judge to score explanations
   - Compare against ground truth labels
   - Provide detailed feedback

3. **Scoring Rubric**
   - Scale: 1-10
   - Criteria:
     - Accuracy (identifies key elements)
     - Completeness (covers all panels)
     - Insight (understands humor/message)
     - Clarity (well-written explanation)

4. **Output Format**
   - Primary: `benchmark_results.csv` with scores
   - Detailed: `benchmark_details.json` with all responses and judge feedback

### Key Decisions
- **Models to Test**: Configurable via `models_config.yaml`
- **Judge Model**: Also configurable (default: Claude)
- **Judge Prompt**: Carefully crafted for consistency
- **Error Handling**: Retry failed API calls, mark as "failed" after 3 attempts
- **Reproducibility**: Save exact prompts, model versions, timestamps
- **Model Runner**: Shared component between Phase 1 and Phase 2

### Output CSV Format
```
model_name, model_version, comic_1_score, comic_2_score, ..., average_score, median_score
claude-3-opus, 2024-02-29, 8.5, 9.0, ..., 8.2, 8.5
gpt-4o, 2024-05-13, 7.5, 8.0, ..., 7.8, 8.0
```

## Phase 3: Static Leaderboard

### Components
1. **Data Processing** (`generate_leaderboard.py`)
   - Convert CSV to JSON for web consumption
   - Calculate statistics (mean, median, std dev)
   - Generate charts data

2. **Static Website** (`index.html`, `style.css`, `script.js`)
   - Responsive design
   - Interactive table with sorting
   - Score distribution visualizations
   - Model details and metadata

3. **Automation**
   - GitHub Actions workflow
   - Runs on push to main branch
   - Updates leaderboard automatically

### Key Decisions
- **Design**: Clean, minimalist with PBF Comics aesthetic nods
- **Features**:
  - Sort by average, median, or individual comic scores
  - Filter by model family or date
  - Show score distributions and trends
  - Detailed view for each model's performance
- **Hosting**: GitHub Pages in `/docs` folder

### Leaderboard Features
- Default sort by average score (descending)
- Columns: Rank, Model, Version, Average, Median, Min, Max, Std Dev
- Expandable rows for detailed per-comic scores
- Export functionality (CSV download)
- Last updated timestamp

## Configuration System

### Model Configuration (`models_config.yaml`)
```yaml
models:
  claude-3-opus:
    provider: anthropic
    model: claude-3-opus-20240229
    api_key_env: ANTHROPIC_API_KEY
    max_tokens: 1000
    temperature: 0.7
    
  gemini-2.5-flash:
    provider: google
    model: gemini-2.5-flash
    api_key_env: GOOGLE_API_KEY
    max_tokens: 1000
    temperature: 0.7
    
  gpt-4o:
    provider: openai
    model: gpt-4o-2024-05-13
    api_key_env: OPENAI_API_KEY
    max_tokens: 1000
    temperature: 0.7
    
  # Easy to add new models
  llama-3:
    provider: together
    model: meta-llama/Llama-3-70b-chat-hf
    api_key_env: TOGETHER_API_KEY
    max_tokens: 1000
    temperature: 0.7

prompts:
  explain_comic: "Explain this comic in 2-3 sentences. Describe what's happening and explain the humor or message."
  
phase1_models: [claude-3-opus, gemini-2.5-flash, gpt-4o]
benchmark_models: [claude-3-opus, gemini-2.5-flash, gpt-4o, llama-3]
judge_model: claude-3-opus
```

### Unified Model Runner (`model_runner.py`)
- Single interface for all model providers
- Handles authentication, rate limiting, retries
- Used by both Phase 1 and Phase 2
- Extensible for new providers

### Benefits of Unified Configuration
- **Consistency**: Same models can be used for ground truth and benchmark
- **Flexibility**: Easy to add/remove models without code changes
- **Reusability**: Phase 1 labeling can be re-run with new models
- **Maintainability**: Single source of truth for model settings
- **Cost Control**: Can test with smaller model sets first

## Pipeline Architecture

```
1. Download Comics (download_pbf_comics_regex.py)
   ↓
2. Generate AI Explanations (generate_explanations.py)
   - Uses models from phase1_models in config
   ↓
3. Human Labeling (labeling_app.py)
   ↓
4. Run Benchmark (run_benchmark.py)
   - Uses models from benchmark_models in config
   ↓
5. Generate Leaderboard (generate_leaderboard.py)
   ↓
6. Deploy to GitHub Pages
```

## Future Enhancements
- Multi-language support
- Different prompts (e.g., "Explain the humor", "Describe the art style")
- Difficulty ratings for comics
- Model fine-tuning experiments
- API for programmatic access to results

## Technical Requirements
- Python 3.8+
- API keys for: Anthropic, Google (Gemini), OpenAI
- ~1GB storage for images
- GitHub repository with Pages enabled

## Estimated Timeline
- Phase 1: 2-3 days (including manual labeling time)
- Phase 2: 1-2 days
- Phase 3: 1 day
- Total: ~1 week for full implementation

## Notes
- Consider rate limits and costs for API usage
- Implement caching to avoid redundant API calls
- Make ground truth labels publicly available for reproducibility
- Consider adding new comics automatically as they're published