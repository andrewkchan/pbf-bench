#!/usr/bin/env python3
"""
Generate AI explanations for all comics using configured models.
This is Phase 1 of the ground truth creation process.
"""
import os
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
from tqdm import tqdm
from dotenv import load_dotenv

from model_runner import ModelRunner, ModelResponse

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExplanationGenerator:
    def __init__(self, 
                 metadata_file: str = "pbf_comics_metadata.json",
                 output_file: str = "ai_explanations.json",
                 config_file: str = "models_config.yaml"):
        """Initialize the explanation generator"""
        self.metadata_file = metadata_file
        self.output_file = output_file
        self.runner = ModelRunner(config_file)
        self.config = self.runner.config
        
        # Load comic metadata
        with open(metadata_file, 'r') as f:
            self.comics_metadata = json.load(f)
        
        # Load existing explanations if any
        self.explanations = self._load_existing_explanations()
    
    def _load_existing_explanations(self) -> Dict:
        """Load existing explanations to support resuming"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    return json.load(f)
            except:
                logger.warning("Could not load existing explanations, starting fresh")
        return {}
    
    def _save_explanations(self):
        """Save explanations to file"""
        with open(self.output_file, 'w') as f:
            json.dump(self.explanations, f, indent=2)
    
    async def generate_for_comic(self, comic: Dict, models: List[str]) -> Dict[str, str]:
        """Generate explanations for a single comic using specified models"""
        image_path = comic['local_path']
        prompt = self.config['prompts']['explain_comic']
        
        # Run all models
        responses = await self.runner.run_models(models, prompt, image_path)
        
        # Extract text from responses
        explanations = {}
        for model_id, response in responses.items():
            if response.error:
                logger.error(f"Error from {model_id} for {comic['filename']}: {response.error}")
                explanations[model_id] = f"[Error: {response.error}]"
            else:
                explanations[model_id] = response.text
        
        return explanations
    
    async def generate_all_explanations(self, 
                                      models: Optional[List[str]] = None,
                                      limit: Optional[int] = None,
                                      skip_existing: bool = True):
        """Generate explanations for all comics"""
        if models is None:
            models = self.config['phase1_models']
        
        comics_to_process = []
        
        # Determine which comics need processing
        for i, comic in enumerate(self.comics_metadata):
            if limit and i >= limit:
                break
            
            comic_id = comic['filename']
            
            # Skip if we already have all explanations for this comic
            if skip_existing and comic_id in self.explanations:
                existing_models = set(self.explanations[comic_id].get('explanations', {}).keys())
                if set(models).issubset(existing_models):
                    continue
            
            comics_to_process.append(comic)
        
        if not comics_to_process:
            logger.info("All comics already have explanations!")
            return
        
        logger.info(f"Generating explanations for {len(comics_to_process)} comics using models: {models}")
        
        # Process in batches to avoid overwhelming the APIs
        batch_size = 5
        
        with tqdm(total=len(comics_to_process), desc="Generating explanations") as pbar:
            for i in range(0, len(comics_to_process), batch_size):
                batch = comics_to_process[i:i+batch_size]
                tasks = []
                
                for comic in batch:
                    task = self.generate_for_comic(comic, models)
                    tasks.append((comic, task))
                
                # Wait for all tasks in batch to complete
                for comic, task in tasks:
                    try:
                        explanations = await task
                        
                        comic_id = comic['filename']
                        
                        # Update explanations
                        if comic_id not in self.explanations:
                            self.explanations[comic_id] = {
                                'comic_title': comic.get('comic_title', ''),
                                'image_path': comic['local_path'],
                                'alt_text': comic.get('alt_text', ''),
                                'explanations': {}
                            }
                        
                        self.explanations[comic_id]['explanations'].update(explanations)
                        
                        # Save after each comic
                        self._save_explanations()
                        
                    except Exception as e:
                        logger.error(f"Failed to process {comic['filename']}: {e}")
                    
                    pbar.update(1)
        
        logger.info(f"Generated explanations saved to {self.output_file}")
    
    def get_statistics(self) -> Dict:
        """Get statistics about generated explanations"""
        stats = {
            'total_comics': len(self.comics_metadata),
            'comics_with_explanations': len(self.explanations),
            'model_counts': {}
        }
        
        # Count explanations per model
        for comic_data in self.explanations.values():
            for model in comic_data.get('explanations', {}):
                stats['model_counts'][model] = stats['model_counts'].get(model, 0) + 1
        
        return stats

async def main():
    parser = argparse.ArgumentParser(description='Generate AI explanations for PBF comics')
    parser.add_argument('--models', nargs='+', help='Models to use (default: from config)')
    parser.add_argument('--limit', type=int, help='Limit number of comics to process')
    parser.add_argument('--no-skip', action='store_true', help='Regenerate existing explanations')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    generator = ExplanationGenerator()
    
    if args.stats:
        stats = generator.get_statistics()
        print("\nExplanation Generation Statistics:")
        print(f"Total comics: {stats['total_comics']}")
        print(f"Comics with explanations: {stats['comics_with_explanations']}")
        print("\nExplanations per model:")
        for model, count in stats['model_counts'].items():
            print(f"  {model}: {count}")
    else:
        await generator.generate_all_explanations(
            models=args.models,
            limit=args.limit,
            skip_existing=not args.no_skip
        )

if __name__ == "__main__":
    asyncio.run(main())