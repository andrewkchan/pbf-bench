#!/usr/bin/env python3
"""
Run the PBF Comics benchmark against specified AI models.
Generates explanations and scores them against ground truth using a judge.
"""
import os
import json
import csv
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from tqdm import tqdm
from dotenv import load_dotenv

from model_runner import ModelRunner, ModelResponse
from judge import ComicExplanationJudge, JudgeScore

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BenchmarkRunner:
    def __init__(self, 
                 config_path: str = "models_config.yaml",
                 ground_truth_file: str = "ground_truth_labels.json",
                 ai_explanations_file: str = "ai_explanations.json",
                 comics_metadata_file: str = "pbf_comics_metadata.json",
                 results_csv: str = "benchmark_results.csv",
                 details_json: str = "benchmark_details.json"):
        """Initialize benchmark runner"""
        self.config_path = config_path
        self.ground_truth_file = ground_truth_file
        self.ai_explanations_file = ai_explanations_file
        self.comics_metadata_file = comics_metadata_file
        self.results_csv = results_csv
        self.details_json = details_json
        
        # Initialize components
        self.runner = ModelRunner(config_path)
        self.judge = ComicExplanationJudge(config_path)
        
        # Load data
        self.ground_truth = self._load_ground_truth()
        self.ai_explanations = self._load_ai_explanations()
        self.comics_metadata = self._load_comics_metadata()
        self.config = self.runner.config
        
        logger.info(f"Loaded {len(self.ground_truth)} ground truth labels")
        logger.info(f"Loaded {len(self.ai_explanations)} AI explanations")
        logger.info(f"Loaded {len(self.comics_metadata)} comics metadata")
    
    def _load_ground_truth(self) -> Dict:
        """Load ground truth labels"""
        if not os.path.exists(self.ground_truth_file):
            raise FileNotFoundError(f"Ground truth file not found: {self.ground_truth_file}")
        
        with open(self.ground_truth_file, 'r') as f:
            return json.load(f)
    
    def _load_ai_explanations(self) -> Dict:
        """Load AI explanations"""
        if not os.path.exists(self.ai_explanations_file):
            logger.warning(f"AI explanations file not found: {self.ai_explanations_file}")
            return {}
        
        with open(self.ai_explanations_file, 'r') as f:
            return json.load(f)
    
    def _load_comics_metadata(self) -> List[Dict]:
        """Load comics metadata"""
        if not os.path.exists(self.comics_metadata_file):
            raise FileNotFoundError(f"Comics metadata file not found: {self.comics_metadata_file}")
        
        with open(self.comics_metadata_file, 'r') as f:
            return json.load(f)
    
    def _get_ground_truth_explanation(self, comic_id: str) -> Optional[str]:
        """Get the ground truth explanation for a comic"""
        if comic_id not in self.ground_truth:
            return None
        
        gt_data = self.ground_truth[comic_id]
        return gt_data.get('explanation')
    
    async def run_single_comic(self, 
                             comic: Dict,
                             models: List[str],
                             ground_truth_explanation: str) -> Dict[str, Any]:
        """Run benchmark on a single comic"""
        comic_id = comic['filename']
        image_path = comic['local_path']
        
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return {
                'comic_id': comic_id,
                'error': f"Image not found: {image_path}",
                'explanations': {},
                'scores': {}
            }
        
        # Generate explanations from all models
        prompt = self.config['prompts']['explain_comic']
        explanations_responses = await self.runner.run_models(models, prompt, image_path)
        
        # Extract text from responses
        explanations = {}
        for model_id, response in explanations_responses.items():
            if response.error:
                logger.warning(f"Error from {model_id} for {comic_id}: {response.error}")
                explanations[model_id] = f"[Error: {response.error}]"
            else:
                explanations[model_id] = response.text
        
        # Judge all explanations
        scores = await self.judge.judge_multiple_explanations(
            image_path,
            ground_truth_explanation,
            explanations
        )
        
        return {
            'comic_id': comic_id,
            'comic_title': comic.get('comic_title', ''),
            'explanations': explanations,
            'scores': {model: {
                'overall_score': score.overall_score,
                'accuracy_score': score.accuracy_score,
                'completeness_score': score.completeness_score,
                'insight_score': score.insight_score,
                'clarity_score': score.clarity_score,
                'reasoning': score.reasoning,
                'timestamp': score.timestamp
            } for model, score in scores.items()},
            'ground_truth': ground_truth_explanation,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def run_benchmark(self, 
                          models: Optional[List[str]] = None,
                          limit: Optional[int] = None,
                          comic_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run full benchmark"""
        if models is None:
            models = self.config['benchmark_models']
        
        logger.info(f"Running benchmark with models: {models}")
        
        # Filter comics based on ground truth availability
        comics_to_test = []
        
        if comic_ids:
            # Test specific comics
            comic_id_to_metadata = {c['filename']: c for c in self.comics_metadata}
            for comic_id in comic_ids:
                if comic_id in comic_id_to_metadata and comic_id in self.ground_truth:
                    comics_to_test.append(comic_id_to_metadata[comic_id])
                else:
                    logger.warning(f"Skipping {comic_id}: not found in metadata or ground truth")
        else:
            # Test all comics with ground truth
            for comic in self.comics_metadata:
                comic_id = comic['filename']
                if comic_id in self.ground_truth:
                    comics_to_test.append(comic)
                    if limit and len(comics_to_test) >= limit:
                        break
        
        if not comics_to_test:
            raise ValueError("No comics found to test. Make sure you have ground truth labels.")
        
        logger.info(f"Testing {len(comics_to_test)} comics")
        
        # Run benchmark on all comics
        results = []
        
        with tqdm(total=len(comics_to_test), desc="Running benchmark") as pbar:
            for comic in comics_to_test:
                comic_id = comic['filename']
                
                # Get ground truth explanation
                gt_explanation = self._get_ground_truth_explanation(comic_id)
                if not gt_explanation:
                    logger.warning(f"No ground truth for {comic_id}, skipping")
                    pbar.update(1)
                    continue
                
                try:
                    result = await self.run_single_comic(comic, models, gt_explanation)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {comic_id}: {e}")
                    results.append({
                        'comic_id': comic_id,
                        'error': str(e),
                        'explanations': {},
                        'scores': {}
                    })
                
                pbar.update(1)
        
        # Calculate summary statistics
        summary = self._calculate_summary_stats(results, models)
        
        benchmark_results = {
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'models': models,
                'total_comics': len(results),
                'config_file': self.config_path,
                'judge_model': self.judge.judge_model_id
            },
            'summary': summary,
            'detailed_results': results
        }
        
        # Save results
        self._save_results(benchmark_results)
        
        return benchmark_results
    
    def _calculate_summary_stats(self, results: List[Dict], models: List[str]) -> Dict:
        """Calculate summary statistics"""
        summary = {}
        
        for model in models:
            scores = []
            accuracy_scores = []
            completeness_scores = []
            insight_scores = []
            clarity_scores = []
            
            for result in results:
                if model in result.get('scores', {}):
                    score_data = result['scores'][model]
                    scores.append(score_data['overall_score'])
                    accuracy_scores.append(score_data['accuracy_score'])
                    completeness_scores.append(score_data['completeness_score'])
                    insight_scores.append(score_data['insight_score'])
                    clarity_scores.append(score_data['clarity_score'])
            
            if scores:
                summary[model] = {
                    'count': len(scores),
                    'overall': {
                        'mean': sum(scores) / len(scores),
                        'median': sorted(scores)[len(scores) // 2],
                        'min': min(scores),
                        'max': max(scores)
                    },
                    'accuracy': {
                        'mean': sum(accuracy_scores) / len(accuracy_scores),
                        'median': sorted(accuracy_scores)[len(accuracy_scores) // 2]
                    },
                    'completeness': {
                        'mean': sum(completeness_scores) / len(completeness_scores),
                        'median': sorted(completeness_scores)[len(completeness_scores) // 2]
                    },
                    'insight': {
                        'mean': sum(insight_scores) / len(insight_scores),
                        'median': sorted(insight_scores)[len(insight_scores) // 2]
                    },
                    'clarity': {
                        'mean': sum(clarity_scores) / len(clarity_scores),
                        'median': sorted(clarity_scores)[len(clarity_scores) // 2]
                    }
                }
            else:
                summary[model] = {
                    'count': 0,
                    'error': 'No successful evaluations'
                }
        
        return summary
    
    def _save_results(self, benchmark_results: Dict):
        """Save results to CSV and JSON files"""
        # Save detailed JSON
        with open(self.details_json, 'w') as f:
            json.dump(benchmark_results, f, indent=2)
        
        logger.info(f"Detailed results saved to {self.details_json}")
        
        # Save CSV summary
        self._save_csv_summary(benchmark_results)
        
        logger.info(f"CSV results saved to {self.results_csv}")
    
    def _save_csv_summary(self, benchmark_results: Dict):
        """Save summary results to CSV"""
        models = benchmark_results['metadata']['models']
        detailed_results = benchmark_results['detailed_results']
        
        # Create CSV with one row per model
        csv_data = []
        
        for model in models:
            row = {
                'model_name': model,
                'model_version': self.config['models'].get(model, {}).get('model', 'unknown'),
                'timestamp': benchmark_results['metadata']['timestamp']
            }
            
            # Add per-comic scores
            for result in detailed_results:
                comic_id = result['comic_id']
                if model in result.get('scores', {}):
                    score = result['scores'][model]['overall_score']
                    row[f'comic_{comic_id}'] = score
                else:
                    row[f'comic_{comic_id}'] = 'ERROR'
            
            # Add summary statistics
            if model in benchmark_results['summary']:
                stats = benchmark_results['summary'][model]
                if 'overall' in stats:
                    row['average_score'] = stats['overall']['mean']
                    row['median_score'] = stats['overall']['median']
                    row['min_score'] = stats['overall']['min']
                    row['max_score'] = stats['overall']['max']
                    row['total_comics'] = stats['count']
                else:
                    row['average_score'] = 'ERROR'
                    row['median_score'] = 'ERROR'
                    row['min_score'] = 'ERROR'
                    row['max_score'] = 'ERROR'
                    row['total_comics'] = 0
            
            csv_data.append(row)
        
        # Write CSV
        if csv_data:
            with open(self.results_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)

async def main():
    parser = argparse.ArgumentParser(description='Run PBF Comics benchmark')
    parser.add_argument('--models', nargs='+', help='Models to test (default: from config)')
    parser.add_argument('--limit', type=int, help='Limit number of comics to test')
    parser.add_argument('--comics', nargs='+', help='Specific comic IDs to test')
    parser.add_argument('--ground-truth', default='ground_truth_labels.json', help='Ground truth labels file')
    parser.add_argument('--ai-explanations', default='ai_explanations.json', help='AI explanations file')
    parser.add_argument('--output-csv', default='benchmark_results.csv', help='Output CSV file')
    parser.add_argument('--output-json', default='benchmark_details.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    try:
        runner = BenchmarkRunner(
            ground_truth_file=args.ground_truth,
            ai_explanations_file=args.ai_explanations,
            results_csv=args.output_csv,
            details_json=args.output_json
        )
        
        results = await runner.run_benchmark(
            models=args.models,
            limit=args.limit,
            comic_ids=args.comics
        )
        
        print("\n" + "="*60)
        print("BENCHMARK RESULTS SUMMARY")
        print("="*60)
        
        for model, stats in results['summary'].items():
            if 'overall' in stats:
                print(f"\n{model}:")
                print(f"  Average Score: {stats['overall']['mean']:.2f}")
                print(f"  Median Score:  {stats['overall']['median']:.2f}")
                print(f"  Comics Tested: {stats['count']}")
            else:
                print(f"\n{model}: {stats.get('error', 'No data')}")
        
        print(f"\nDetailed results saved to: {args.output_json}")
        print(f"CSV results saved to: {args.output_csv}")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())