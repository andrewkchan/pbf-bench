#!/usr/bin/env python3
"""
Judge system for scoring AI explanations against ground truth.
Uses a strong AI model to provide consistent scoring.
"""
import os
import json
import asyncio
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from model_runner import ModelRunner, ModelResponse

logger = logging.getLogger(__name__)

@dataclass
class JudgeScore:
    """Score from the judge with detailed breakdown"""
    overall_score: float  # 1-10
    accuracy_score: float  # 1-10 (identifies key elements correctly)
    completeness_score: float  # 1-10 (covers all important aspects)
    insight_score: float  # 1-10 (understands humor/message)
    clarity_score: float  # 1-10 (well-written explanation)
    reasoning: str  # Judge's explanation of the score
    timestamp: str
    judge_model: str

class ComicExplanationJudge:
    """Judge for scoring comic explanations"""
    
    def __init__(self, config_path: str = "models_config.yaml"):
        """Initialize judge with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.judge_model_id = self.config.get('judge_model', 'claude-3-opus')
        self.runner = ModelRunner(config_path)
        
        # Create the judge prompt template
        self.judge_prompt_template = """You are an expert judge evaluating AI explanations of comic strips. Your task is to score an AI model's explanation against a high-quality ground truth explanation.

**Comic Image**: [The judge will see the comic image]

**Ground Truth Explanation**: {ground_truth}

**AI Model Explanation**: {model_explanation}

**Scoring Criteria** (each scored 1-10):
1. **Accuracy**: Does the AI explanation correctly identify what's happening in the comic?
2. **Completeness**: Does it cover all important visual elements and story beats?
3. **Insight**: Does it understand and explain the humor, irony, or message?
4. **Clarity**: Is the explanation well-written and easy to understand?

**Instructions**:
- Compare the AI explanation to the ground truth explanation
- The AI explanation doesn't need to be identical to ground truth, just accurate and comprehensive
- Consider that there can be multiple valid interpretations
- Focus on factual accuracy and understanding rather than writing style
- Be fair but rigorous in your evaluation

**Response Format**:
Provide your scores as a JSON object in a code block. IMPORTANT: The "reasoning" field must be a single line string without newlines. Use spaces or semicolons to separate thoughts.

```json
{{
    "accuracy_score": X.X,
    "completeness_score": X.X,
    "insight_score": X.X,
    "clarity_score": X.X,
    "overall_score": X.X,
    "reasoning": "Detailed explanation of your scoring reasoning highlighting what the AI explanation did well and where it fell short compared to the ground truth. Keep this as a single line without newlines."
}}
```

The overall_score should be a weighted average: (accuracy * 0.4 + completeness * 0.25 + insight * 0.25 + clarity * 0.1)"""

    async def judge_explanation(self, 
                              comic_image_path: str,
                              ground_truth: str, 
                              model_explanation: str,
                              model_name: str = "unknown") -> JudgeScore:
        """Judge a single explanation against ground truth"""
        
        # Check if we're using an Anthropic model and can use structured output
        if self.judge_model_id.startswith('claude') and self.config['models'][self.judge_model_id]['provider'] == 'anthropic':
            return await self._judge_with_anthropic_structured(
                comic_image_path, ground_truth, model_explanation, model_name
            )
        
        # Otherwise use the standard approach with text parsing
        return await self._judge_with_text_parsing(comic_image_path, ground_truth, model_explanation, model_name)
    
    async def _judge_with_anthropic_structured(self,
                                              comic_image_path: str,
                                              ground_truth: str,
                                              model_explanation: str,
                                              model_name: str) -> JudgeScore:
        """Use Anthropic's structured output for judging"""
        try:
            import anthropic
            import base64
            
            # Get API key from config
            api_key = os.getenv(self.config['models'][self.judge_model_id]['api_key_env'])
            client = anthropic.Anthropic(api_key=api_key)
            
            # Read and encode image
            with open(comic_image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            media_type = "image/png" if comic_image_path.endswith('.png') else "image/jpeg"
            
            # Create prompt
            prompt = f"""You are an expert judge evaluating AI explanations of comic strips. Your task is to score an AI model's explanation against a high-quality ground truth explanation.

**Ground Truth Explanation**: {ground_truth}

**AI Model Explanation**: {model_explanation}

Evaluate the AI explanation on these criteria:
1. **Accuracy** (weight 40%): Does it correctly identify what's happening?
2. **Completeness** (weight 25%): Does it cover all important visual elements?
3. **Insight** (weight 25%): Does it understand the humor or message?
4. **Clarity** (weight 10%): Is it well-written and easy to understand?

The AI explanation doesn't need to be identical to ground truth, just accurate and comprehensive."""
            
            # Use tool/function calling for structured output
            message = client.messages.create(
                model=self.config['models'][self.judge_model_id]['model'],
                max_tokens=self.config['models'][self.judge_model_id]['max_tokens'],
                temperature=self.config['models'][self.judge_model_id]['temperature'],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }],
                tools=[{
                    "name": "score_explanation",
                    "description": "Score an AI explanation of a comic against ground truth",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "accuracy_score": {
                                "type": "number",
                                "description": "Score 1-10 for how accurately the AI identifies what's happening",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "completeness_score": {
                                "type": "number",
                                "description": "Score 1-10 for coverage of all important visual elements",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "insight_score": {
                                "type": "number",
                                "description": "Score 1-10 for understanding the humor or message",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "clarity_score": {
                                "type": "number",
                                "description": "Score 1-10 for how well-written the explanation is",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "overall_score": {
                                "type": "number",
                                "description": "Weighted average: (accuracy * 0.4 + completeness * 0.25 + insight * 0.25 + clarity * 0.1)",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Detailed explanation of the scoring, highlighting strengths and weaknesses"
                            }
                        },
                        "required": ["accuracy_score", "completeness_score", "insight_score", "clarity_score", "overall_score", "reasoning"]
                    }
                }],
                tool_choice={"type": "tool", "name": "score_explanation"}
            )
            
            # Extract the tool use response
            tool_use = None
            for content in message.content:
                if content.type == 'tool_use' and content.name == 'score_explanation':
                    tool_use = content
                    break
            
            if not tool_use:
                logger.error("No tool use found in Anthropic response")
                return self._create_error_score("No structured output from judge")
            
            # The input should be our scores
            scores = tool_use.input
            
            return JudgeScore(
                overall_score=float(scores['overall_score']),
                accuracy_score=float(scores['accuracy_score']),
                completeness_score=float(scores['completeness_score']),
                insight_score=float(scores['insight_score']),
                clarity_score=float(scores['clarity_score']),
                reasoning=scores['reasoning'],
                timestamp=datetime.utcnow().isoformat(),
                judge_model=self.judge_model_id
            )
            
        except Exception as e:
            logger.error(f"Error with Anthropic structured output: {e}")
            # Fall back to text parsing approach
            return await self._judge_with_text_parsing(comic_image_path, ground_truth, model_explanation, model_name)
    
    async def _judge_with_text_parsing(self,
                                     comic_image_path: str,
                                     ground_truth: str,
                                     model_explanation: str,
                                     model_name: str) -> JudgeScore:
        """Use traditional text parsing for judging"""
        # Format the prompt
        prompt = self.judge_prompt_template.format(
            ground_truth=ground_truth,
            model_explanation=model_explanation
        )
        
        try:
            # Get judge response
            response = await self.runner.run_model(
                self.judge_model_id, 
                prompt, 
                comic_image_path
            )
            
            if response.error:
                logger.error(f"Judge model error for {model_name}: {response.error}")
                return self._create_error_score(response.error)
            
            # Parse the JSON response
            judge_output = self._parse_judge_response(response.text)
            
            if not judge_output:
                logger.error(f"Failed to parse judge response for {model_name}")
                return self._create_error_score("Failed to parse judge response")
            
            # Create structured score
            return JudgeScore(
                overall_score=judge_output.get('overall_score', 0.0),
                accuracy_score=judge_output.get('accuracy_score', 0.0),
                completeness_score=judge_output.get('completeness_score', 0.0),
                insight_score=judge_output.get('insight_score', 0.0),
                clarity_score=judge_output.get('clarity_score', 0.0),
                reasoning=judge_output.get('reasoning', ''),
                timestamp=datetime.utcnow().isoformat(),
                judge_model=self.judge_model_id
            )
            
        except Exception as e:
            logger.error(f"Error judging explanation for {model_name}: {e}")
            return self._create_error_score(str(e))
    
    def _parse_judge_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from judge response"""
        try:
            # First try to find JSON in a code block
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Fallback: Try to find JSON object directly
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    logger.warning("No JSON found in judge response")
                    return None
                
                json_str = response_text[start_idx:end_idx]
            
            # Parse the JSON
            result = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['accuracy_score', 'completeness_score', 'insight_score', 'clarity_score', 'overall_score', 'reasoning']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing field {field} in judge response")
                    return None
            
            # Ensure scores are floats
            for field in ['accuracy_score', 'completeness_score', 'insight_score', 'clarity_score', 'overall_score']:
                if field in result:
                    result[field] = float(result[field])
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"JSON string that failed: {json_str[:200]}...")
            
            # Try to extract scores using regex as fallback
            try:
                scores = {}
                score_patterns = {
                    'accuracy_score': r'"accuracy_score"\s*:\s*([\d.]+)',
                    'completeness_score': r'"completeness_score"\s*:\s*([\d.]+)',
                    'insight_score': r'"insight_score"\s*:\s*([\d.]+)',
                    'clarity_score': r'"clarity_score"\s*:\s*([\d.]+)',
                    'overall_score': r'"overall_score"\s*:\s*([\d.]+)'
                }
                
                for field, pattern in score_patterns.items():
                    match = re.search(pattern, response_text)
                    if match:
                        scores[field] = float(match.group(1))
                
                # Extract reasoning (may contain newlines)
                reasoning_pattern = r'"reasoning"\s*:\s*"(.*?)"(?:\s*[,}])'
                reasoning_match = re.search(reasoning_pattern, response_text, re.DOTALL)
                if reasoning_match:
                    scores['reasoning'] = reasoning_match.group(1)
                else:
                    scores['reasoning'] = "Failed to extract reasoning"
                
                # Check if we got all required fields
                if all(field in scores for field in required_fields):
                    logger.info("Successfully extracted scores using regex fallback")
                    return scores
                
            except Exception as e2:
                logger.error(f"Regex fallback also failed: {e2}")
            
            return None
        except Exception as e:
            logger.error(f"Error parsing judge response: {e}")
            return None
    
    def _create_error_score(self, error_message: str) -> JudgeScore:
        """Create a score object for errors"""
        return JudgeScore(
            overall_score=0.0,
            accuracy_score=0.0,
            completeness_score=0.0,
            insight_score=0.0,
            clarity_score=0.0,
            reasoning=f"Error: {error_message}",
            timestamp=datetime.utcnow().isoformat(),
            judge_model=self.judge_model_id
        )

    async def judge_multiple_explanations(self, 
                                        comic_image_path: str,
                                        ground_truth: str,
                                        explanations: Dict[str, str]) -> Dict[str, JudgeScore]:
        """Judge multiple explanations for the same comic"""
        tasks = []
        
        for model_name, explanation in explanations.items():
            task = self.judge_explanation(
                comic_image_path, 
                ground_truth, 
                explanation, 
                model_name
            )
            tasks.append((model_name, task))
        
        results = {}
        for model_name, task in tasks:
            score = await task
            results[model_name] = score
        
        return results

# Example usage and testing
if __name__ == "__main__":
    async def test_judge():
        judge = ComicExplanationJudge()
        
        # Test with sample data
        comic_path = "pbf_comics/PBF-Bright.png"
        ground_truth = "A comic showing paintbrushes as a family, where the child is a toothbrush going to dentistry school, representing how children sometimes choose different career paths than their parents."
        
        test_explanations = {
            "good_explanation": "The comic shows paintbrush parents sending their toothbrush child to dental school, representing how kids choose different careers than their parents.",
            "poor_explanation": "This comic shows some brushes talking to each other.",
            "wrong_explanation": "The comic depicts cars racing on a track."
        }
        
        if os.path.exists(comic_path):
            scores = await judge.judge_multiple_explanations(
                comic_path, 
                ground_truth, 
                test_explanations
            )
            
            print("Judge Test Results:")
            for model, score in scores.items():
                print(f"\n{model}:")
                print(f"  Overall: {score.overall_score:.1f}")
                print(f"  Accuracy: {score.accuracy_score:.1f}")
                print(f"  Reasoning: {score.reasoning[:100]}...")
        else:
            print(f"Test comic not found: {comic_path}")
    
    asyncio.run(test_judge())