# PBF Comics AI Benchmark

[<img src="/docs/pbf-sample.png">](https://pbfcomics.com/comics/trunkle/)

This repository contains the static leaderboard webpage and the source code to generate and evaluate the PBF Comics Benchmark. The goal of this benchmark is to evaluate AI model visual understanding and comic explanation using a dataset of 285 comics from Nicholas Gurewitch's Perry Bible Fellowship comics (https://pbfcomics.com/). These comics are interesting because:
- They're **highly visual**, unlike other popular comics such as XKCD or Saturday Morning Breakfast Comics, which derive much humor from captions. Many comics in the series [do not have any words at all](https://pbfcomics.com/comics/trunkle/). 
- There is **diversity of styles, entities, and situations** in the series. While the early PBF comics feature mostly human characters with a similar cartoony style, the series as a whole has a mix of [black-and-white](https://pbfcomics.com/comics/dinosaur-sheriff/), [watercolor](https://pbfcomics.com/comics/clear-boundaries/), [cartoon](https://pbfcomics.com/comics/the-shrink-ray/), and [realistic](https://pbfcomics.com/comics/carolyn-vert/) visual styles, [animal](https://pbfcomics.com/comics/the-last-unicorns/), [human](https://pbfcomics.com/comics/food-fight/), [anthropomorphic](https://pbfcomics.com/comics/shocked/), and [abstract](https://pbfcomics.com/comics/big-numbers/) characters.
- The **themes are complex** and ranges from [slapstick humor](https://pbfcomics.com/comics/mrs-hammer/) to [subversions of common tropes in pop culture](https://pbfcomics.com/comics/atlantis/). Sometimes the humor comes from [what's left out of the picture](https://pbfcomics.com/comics/nude-beach/) and sometimes it comes from how the [visual styles of the picture are creatively mixed](https://pbfcomics.com/comics/night-shift/). Unlike other series which have existing datasets such as ["Yes, But"](https://huggingface.co/datasets/zhehuderek/YESBUT_Benchmark), there is no single format that comics follow. Some comics are just a [single panel](https://pbfcomics.com/comics/bright/) while [others have dozens](https://pbfcomics.com/comics/trauma-trooper/).
- They are **not yet perfectly understood by AI**. As of mid-2025, while the series is well-known and has been on the internet long enough that frontier models know about it, individual comics do not have enough material about them online for their themes or messages to be memorized by models. The crude comic humor is also not yet well understood by AI models (as also seen in [Hu 2024](https://pbfcomics.com/comics/trauma-trooper/)).

## Methodology

### Ground truth labels

Each comic was assigned a ground truth label (explanation of the comic) by first generating candidate labels from GPT-4o, Claude 3.5 Sonnet, and Gemini 2.0 Flash with the prompt "Explain this comic. Describe what's happening and explain the humor or message." using the `generate_explanations.py` script, then having a human labeler either select the best candidate label or write their own label using the webapp found in `labeling_app.py`. This was a labor-saving measure; most of the final labels ended up with moderate to significant human modifications on top of the candidates. 

### Benchmark scores

The benchmark tasks models with explaining each comic via the same prompt as above. Explanations are collected for all 285 comics. Claude 4 Opus is then [used as a judge](https://arxiv.org/abs/2306.05685) to grade the predicted explanation for a given comic; it is given the predicted explanation, the ground truth explanation, and the comic image, and gives scores (1-10) on:
1. **Accuracy** (weight 40%): Does it correctly identify what's happening?
2. **Completeness** (weight 25%): Does it cover all important visual elements?
3. **Insight** (weight 25%): Does it understand the humor or message?
4. **Clarity** (weight 10%): Is it well-written and easy to understand?

See `judge.py` for more. The overall score is a weighted sum of these individual scores.

## Running the benchmark

To run the benchmark and update the leaderboard with new results, make a `.env` file in the root directory containing your API keys from the `.env.example` template, then:

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