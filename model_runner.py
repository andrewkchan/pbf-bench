#!/usr/bin/env python3
"""
Unified model runner for multiple AI providers.
Handles authentication, rate limiting, and retries.
"""
import os
import time
import base64
import asyncio
import tempfile
import atexit
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import yaml
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Track temporary files for cleanup
_temp_files = []

def _cleanup_temp_files():
    """Clean up temporary files on exit"""
    for temp_file in _temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                logger.debug(f"Cleaned up temporary file: {temp_file}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
    _temp_files.clear()

# Register cleanup function
atexit.register(_cleanup_temp_files)

@dataclass
class ModelResponse:
    """Standard response format from any model"""
    model_id: str
    text: str
    usage: Dict[str, int]
    latency_ms: float
    timestamp: str
    error: Optional[str] = None

class ModelProvider(ABC):
    """Abstract base class for model providers"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv(config['api_key_env'])
        if not self.api_key:
            raise ValueError(f"API key not found in environment variable: {config['api_key_env']}")
    
    @abstractmethod
    async def generate(self, prompt: str, image_path: str) -> ModelResponse:
        """Generate a response for the given prompt and image"""
        pass
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _ensure_compatible_format(self, image_path: str) -> str:
        """Convert image to compatible format if needed (e.g., GIF to PNG).
        This ensures consistency across all providers."""
        if not image_path.lower().endswith('.gif'):
            return image_path
        
        try:
            from PIL import Image
            
            # Create a temporary PNG file
            temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_png_path = temp_png.name
            temp_png.close()
            
            # Convert GIF to PNG
            with Image.open(image_path) as img:
                # Get the first frame if it's an animated GIF
                if hasattr(img, 'n_frames') and img.n_frames > 1:
                    img.seek(0)
                # Convert to RGB if necessary (some GIFs might be in palette mode)
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                img.save(temp_png_path, 'PNG')
            
            # Track for cleanup
            _temp_files.append(temp_png_path)
            
            logger.info(f"Converted GIF to PNG: {image_path} -> {temp_png_path}")
            return temp_png_path
            
        except Exception as e:
            logger.warning(f"Failed to convert GIF to PNG: {e}. Using original file.")
            return image_path

class AnthropicProvider(ModelProvider):
    """Provider for Anthropic Claude models"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import anthropic
            logger.info(f"Anthropic version: {anthropic.__version__}")
            # Initialize with explicit parameters only
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                max_retries=0  # We handle retries ourselves
            )
            logger.info("✅ Anthropic client initialized successfully")
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise
    
    async def generate(self, prompt: str, image_path: str) -> ModelResponse:
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Convert GIF to PNG if needed for compatibility
            compatible_path = self._ensure_compatible_format(image_path)
            
            # Read image and determine media type
            image_data = self.encode_image(compatible_path)
            media_type = "image/png" if compatible_path.endswith('.png') else "image/jpeg"
            
            # Create message with image
            message = self.client.messages.create(
                model=self.config['model'],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature'],
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
                }]
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ModelResponse(
                model_id=self.config['model'],
                text=message.content[0].text,
                usage={
                    'input_tokens': message.usage.input_tokens,
                    'output_tokens': message.usage.output_tokens,
                    'total_tokens': message.usage.input_tokens + message.usage.output_tokens
                },
                latency_ms=latency_ms,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error with Anthropic API: {e}")
            return ModelResponse(
                model_id=self.config['model'],
                text="",
                usage={},
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=timestamp,
                error=str(e)
            )

class GoogleProvider(ModelProvider):
    """Provider for Google Gemini models"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import google.generativeai as genai
            logger.info(f"Google Generative AI version: {genai.__version__}")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(config['model'])
            logger.info("✅ Google Gemini client initialized successfully")
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Failed to initialize Google client: {e}")
            raise
    
    async def generate(self, prompt: str, image_path: str) -> ModelResponse:
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Convert GIF to PNG if needed for compatibility
            compatible_path = self._ensure_compatible_format(image_path)
            
            import PIL.Image
            image = PIL.Image.open(compatible_path)
            
            # Generate content
            response = self.model.generate_content(
                [prompt, image],
                generation_config={
                    'temperature': self.config['temperature'],
                    'max_output_tokens': self.config['max_tokens'],
                }
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract token usage if available
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    'input_tokens': response.usage_metadata.prompt_token_count,
                    'output_tokens': response.usage_metadata.candidates_token_count,
                    'total_tokens': response.usage_metadata.total_token_count
                }
            
            return ModelResponse(
                model_id=self.config['model'],
                text=response.text,
                usage=usage,
                latency_ms=latency_ms,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error with Google API: {e}")
            return ModelResponse(
                model_id=self.config['model'],
                text="",
                usage={},
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=timestamp,
                error=str(e)
            )

class OpenAIProvider(ModelProvider):
    """Provider for OpenAI GPT models"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import openai
            logger.info(f"OpenAI version: {openai.__version__}")
            # Initialize with explicit parameters only
            self.client = openai.OpenAI(
                api_key=self.api_key,
                max_retries=0  # We handle retries ourselves
            )
            logger.info("✅ OpenAI client initialized successfully")
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    async def generate(self, prompt: str, image_path: str) -> ModelResponse:
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Convert GIF to PNG if needed for consistency
            compatible_path = self._ensure_compatible_format(image_path)
            
            # Encode image
            image_data = self.encode_image(compatible_path)
            
            # Create completion
            response = self.client.chat.completions.create(
                model=self.config['model'],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature']
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ModelResponse(
                model_id=self.config['model'],
                text=response.choices[0].message.content,
                usage={
                    'input_tokens': response.usage.prompt_tokens,
                    'output_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                latency_ms=latency_ms,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}")
            return ModelResponse(
                model_id=self.config['model'],
                text="",
                usage={},
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=timestamp,
                error=str(e)
            )

class ModelRunner:
    """Main class for running models with rate limiting and retries"""
    
    PROVIDER_CLASSES = {
        'anthropic': AnthropicProvider,
        'google': GoogleProvider,
        'openai': OpenAIProvider
    }
    
    def __init__(self, config_path: str = "models_config.yaml"):
        """Initialize with configuration file"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.providers = {}
        self.rate_limiters = {}
        self._init_providers()
    
    def _init_providers(self):
        """Initialize provider instances"""
        required_providers = set()
        
        # Determine which providers are actually needed
        for model_id, model_config in self.config['models'].items():
            required_providers.add(model_config['provider'])
        
        failed_providers = []
        
        for provider_name in required_providers:
            if provider_name not in self.providers:
                provider_class = self.PROVIDER_CLASSES.get(provider_name)
                if not provider_class:
                    failed_providers.append(f"Unknown provider: {provider_name}")
                    continue
                
                try:
                    # Find a model config for this provider
                    model_config = None
                    for _, config in self.config['models'].items():
                        if config['provider'] == provider_name:
                            model_config = config
                            break
                    
                    self.providers[provider_name] = provider_class(model_config)
                    # Initialize rate limiter
                    rate_limit = self.config['rate_limits'].get(provider_name, 60)
                    self.rate_limiters[provider_name] = RateLimiter(rate_limit)
                    logger.info(f"✅ Initialized provider: {provider_name}")
                except Exception as e:
                    error_msg = f"Failed to initialize provider {provider_name}: {e}"
                    logger.error(error_msg)
                    failed_providers.append(error_msg)
        
        if failed_providers:
            logger.error("❌ Failed to initialize required providers:")
            for error in failed_providers:
                logger.error(f"  - {error}")
            raise RuntimeError(f"Provider initialization failed. Please check your API keys and dependencies.")
    
    async def run_model(self, model_id: str, prompt: str, image_path: str) -> ModelResponse:
        """Run a specific model with rate limiting and retries"""
        if model_id not in self.config['models']:
            raise ValueError(f"Unknown model: {model_id}")
        
        model_config = self.config['models'][model_id]
        provider_name = model_config['provider']
        provider = self.providers.get(provider_name)
        
        if not provider:
            return ModelResponse(
                model_id=model_id,
                text="",
                usage={},
                latency_ms=0,
                timestamp=datetime.utcnow().isoformat(),
                error=f"Provider {provider_name} not initialized"
            )
        
        # Apply rate limiting
        rate_limiter = self.rate_limiters.get(provider_name)
        if rate_limiter:
            await rate_limiter.acquire()
        
        # Retry logic
        retry_config = self.config.get('retry', {})
        max_attempts = retry_config.get('max_attempts', 3)
        delay = retry_config.get('initial_delay', 1)
        backoff = retry_config.get('backoff_factor', 2)
        
        for attempt in range(max_attempts):
            response = await provider.generate(prompt, image_path)
            
            if not response.error:
                return response
            
            if attempt < max_attempts - 1:
                logger.warning(f"Attempt {attempt + 1} failed for {model_id}: {response.error}")
                await asyncio.sleep(delay)
                delay *= backoff
        
        return response
    
    async def run_models(self, model_ids: List[str], prompt: str, image_path: str) -> Dict[str, ModelResponse]:
        """Run multiple models in parallel"""
        tasks = []
        for model_id in model_ids:
            task = self.run_model(model_id, prompt, image_path)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        return {model_id: response for model_id, response in zip(model_ids, responses)}

class RateLimiter:
    """Simple rate limiter using token bucket algorithm"""
    def __init__(self, rate: int):
        self.rate = rate  # requests per minute
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / 60))
            self.last_update = now
            
            if self.tokens < 1:
                sleep_time = (1 - self.tokens) * (60 / self.rate)
                await asyncio.sleep(sleep_time)
                self.tokens = 1
            
            self.tokens -= 1

# Example usage
if __name__ == "__main__":
    async def test():
        runner = ModelRunner()
        
        # Test with a sample image
        test_image = "pbf_comics/PBF-Bright.png"
        if os.path.exists(test_image):
            prompt = runner.config['prompts']['explain_comic']
            
            # Test single model
            response = await runner.run_model('claude-3-5-sonnet', prompt, test_image)
            print(f"Claude response: {response.text[:100]}...")
            
            # Test multiple models
            models = runner.config['phase1_models']
            responses = await runner.run_models(models, prompt, test_image)
            for model_id, response in responses.items():
                print(f"\n{model_id}: {response.text[:100]}...")
    
    asyncio.run(test())