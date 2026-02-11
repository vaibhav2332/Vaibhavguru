import asyncio
import logging
import os
import json
import re
import aiosqlite
import httpx
import html
import random
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from utils.misc import modules_help, prefix

# =================================================================================================
# ⚙️ SYSTEM CONFIGURATION
# =================================================================================================

class Config:
    DB_NAME = "userbot_gems_v3.db"
    # Increased history depth for better "long term" conversation memory
    MAX_HISTORY_DEPTH = 30 
    IMGBB_KEY = "afcf96b3fa068c1ce3ea7f5d90b2c849"
    
    # Enhanced Image Generation API Configuration
    INFIP_API_KEY = random.choice(["infip-4ccc6287", "infip-30f9b23c", "infip-820535e7", "infip-30a7d4bc", "infip-551dc9e9"])  # Will be auto-generated or loaded from env
    INFIP_BASE_URL = "https://api.infip.pro"
    INFIP_HEADERS = {
        "Content-Type": "application/json",
        "User-Agent": "PyGem-Userbot/1.0"
    }
    
    # Default Image Generation Settings (Enhanced)
    DEFAULT_IMG_MODEL = "phoenix"
    DEFAULT_IMG_SIZE = "1024x1024"
    DEFAULT_IMG_COUNT = 1
    DEFAULT_IMG_QUALITY = "standard"  # standard, hd
    DEFAULT_IMG_STYLE = "vivid"  # vivid, natural
    
    # All Available Image Models from Infip API
    AVAILABLE_IMG_MODELS = {
        "img3": {"tier": "free", "description": "Basic image generation"},
        "img4": {"tier": "free", "description": "Enhanced basic generation"},
        "z-image-turbo": {"tier": "free", "description": "Fast generation", "async": True},
        "nbpro": {"tier": "pro", "description": "Professional quality", "async": True},
        "nano-banana": {"tier": "pro", "description": "High-end model", "async": True},
        "qwen": {"tier": "free", "description": "Qwen model", "async": True},
        "flux-schnell": {"tier": "free", "description": "Fast Flux model"},
        "flux2-klein-9b": {"tier": "free", "description": "Flux 2 Klein 9B"},
        "flux2-klein-4b": {"tier": "free", "description": "Flux 2 Klein 4B"},
        "flux2-dev": {"tier": "free", "description": "Flux 2 Development"},
        "lucid-origin": {"tier": "free", "description": "Lucid Origin model"},
        "phoenix": {"tier": "free", "description": "Phoenix model"},
        "sdxl": {"tier": "free", "description": "Stable Diffusion XL"},
        "sdxl-lite": {"tier": "free", "description": "Lightweight SDXL"},
        "dreamshaper": {"tier": "free", "description": "Artistic DreamShaper"}
    }
    
    # Voice/Audio Generation Settings
    ENABLE_VOICE_GENERATION = True
    DEFAULT_VOICE_MODEL = "tts-1"
    DEFAULT_VOICE_SPEED = 1.0
    
    # Smart Reply Settings
    ENABLE_SMART_REPLIES = True
    SMART_REPLY_CONFIDENCE = 0.7
    AUTO_REPLY_DELAY = (1.0, 3.0)  # min, max seconds
    
    # Content Moderation
    ENABLE_CONTENT_FILTER = True
    CONTENT_FILTER_STRICTNESS = "medium"  # low, medium, high
    
    # Translation Settings
    ENABLE_AUTO_TRANSLATE = True
    DEFAULT_SOURCE_LANG = "auto"
    DEFAULT_TARGET_LANG = "en"
    
    # Memory & Learning Settings
    ENABLE_CONTINUOUS_LEARNING = True
    LEARNING_BATCH_SIZE = 10
    AUTO_SAVE_INTERVAL = 300  # seconds
    
    # API Rate Limiting (Enhanced)
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000
    API_TIMEOUT = 60.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    # Performance Settings
    ENABLE_PARALLEL_PROCESSING = True
    MAX_CONCURRENT_REQUESTS = 3
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # seconds
    
    # Cookies & Headers for AI Service
    AUTH_COOKIES = {
        'abIDV2': '546', 'anonID': 'f7ceed385778e221', 'premium': 'false',
        'acceptedPremiumModesTnc': 'false', '_sp_ses.48cd': '*',
        'connect.sid': 's%3AoNTyr66sFMpJww2YC1k9jsS5rG8gfAh_.Sm0N0bBqdEBKfsYVLxJ%2FePg%2B%2FyDjynTPY69eA57QGIk',
        'qdid': '78e86ed47333249550c398b65d45ad12', 'authenticated': 'true',
        '_sp_id.48cd': '37c7e1f4-cd04-4797-afdf-d0b8e6ae880f.1760000217.3.1765560556.1765046295'
    }
    AUTH_HEADERS = {
        'accept': 'text/event-stream', 'accept-language': 'en-US,en;q=0.7',
        'content-type': 'application/json', 'origin': 'https://quillbot.com',
        'referer': 'https://quillbot.com/ai-chat',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'webapp-version': '38.25.1'
    }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PyGem_System")

# =================================================================================================
# 📊 API USAGE MONITORING & VISUALS
# =================================================================================================

class UIHelper:
    """Helper methods for better visuals."""
    @staticmethod
    def progress_bar(current: int, total: int, length: int = 10) -> str:
        """Generates a visual progress bar string."""
        percent = min(1.0, current / total) if total > 0 else 0
        filled = int(length * percent)
        bar = "█" * filled + "░" * (length - filled)
        return bar

class APIMonitor:
    """Monitors and manages API usage with rate limiting."""
    
    def __init__(self):
        self.request_times = []
        self.hourly_requests = []
        self.daily_usage = {
            'ai_requests': 0,
            'image_uploads': 0,
            'errors': 0,
            'last_reset': datetime.now().date()
        }
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        async with self._lock:
            now = time.time()
            
            # Clean old requests (older than 1 hour)
            self.request_times = [t for t in self.request_times if now - t < 3600]
            self.hourly_requests = [t for t in self.hourly_requests if now - t < 3600]
            
            # Check minute limit
            minute_requests = [t for t in self.request_times if now - t < 60]
            if len(minute_requests) >= Config.MAX_REQUESTS_PER_MINUTE:
                logger.warning(f"Rate limit exceeded: {len(minute_requests)}/min")
                return False
            
            # Check hour limit
            if len(self.hourly_requests) >= Config.MAX_REQUESTS_PER_HOUR:
                logger.warning(f"Hourly rate limit exceeded: {len(self.hourly_requests)}/hour")
                return False
            
            return True
    
    async def record_request(self, request_type: str = 'ai'):
        """Record an API request."""
        async with self._lock:
            now = time.time()
            self.request_times.append(now)
            self.hourly_requests.append(now)
            
            # Reset daily counters if needed
            if datetime.now().date() > self.daily_usage['last_reset']:
                self.daily_usage = {
                    'ai_requests': 0,
                    'image_uploads': 0,
                    'errors': 0,
                    'last_reset': datetime.now().date()
                }
            
            # Update counters
            if request_type == 'ai':
                self.daily_usage['ai_requests'] += 1
            elif request_type == 'image':
                self.daily_usage['image_uploads'] += 1
    
    async def record_error(self):
        """Record an API error."""
        async with self._lock:
            self.daily_usage['errors'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        now = time.time()
        minute_requests = len([t for t in self.request_times if now - t < 60])
        hour_requests = len(self.hourly_requests)
        
        return {
            'requests_per_minute': minute_requests,
            'requests_per_hour': hour_requests,
            'daily_ai_requests': self.daily_usage['ai_requests'],
            'daily_image_uploads': self.daily_usage['image_uploads'],
            'daily_errors': self.daily_usage['errors'],
            'last_reset': self.daily_usage['last_reset'].isoformat()
        }

API_MONITOR = APIMonitor()

class ImageGenerator:
    """Enhanced Image Generation with Infip API."""
    
    def __init__(self):
        self.base_url = Config.INFIP_BASE_URL
        self.api_key = Config.INFIP_API_KEY or os.getenv("INFIP_API_KEY", "")
        self.headers = Config.INFIP_HEADERS.copy()
        self.cache = {} if Config.CACHE_ENABLED else None
        self.last_key_check = 0
        
    async def setup_api_key(self) -> bool:
        """Enhanced API key setup with multiple fallback methods."""
        try:
            current_time = time.time()
            
            # Check if we recently validated the key (cache for 5 minutes)
            if current_time - self.last_key_check < 300 and self.api_key:
                return True
            
            # Method 1: Try environment variable
            if not self.api_key:
                env_key = os.getenv("INFIP_API_KEY")
                if env_key and env_key != "infip-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
                    self.api_key = env_key
                    Config.INFIP_API_KEY = env_key
            
            # Method 2: Try to generate new key
            if not self.api_key or self.api_key == "infip-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{self.base_url}/v1/api-keys")
                    if response.status_code == 200:
                        data = response.json()
                        self.api_key = data.get("api_key", "")
                        Config.INFIP_API_KEY = self.api_key
                        logger.info(f"Generated new API key: {self.api_key[:20]}...")
                    else:
                        logger.error(f"Failed to generate API key: {response.status_code}")
                        return False
            
            # Method 3: Validate existing key
            if self.api_key:
                if await self.validate_api_key():
                    self.last_key_check = current_time
                    return True
                else:
                    logger.warning("API key validation failed, trying to generate new one")
                    self.api_key = ""
                    return await self.setup_api_key()
            
            return False
            
        except Exception as e:
            logger.error(f"API key setup error: {e}")
            return False
    
    async def validate_api_key(self) -> bool:
        """Enhanced API key validation with rate limit check."""
        try:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
                if response.status_code == 200:
                    logger.info("API key validated successfully")
                    return True
                elif response.status_code == 429:
                    logger.warning("API rate limit reached during validation")
                    return True  # Assume valid but rate limited
                else:
                    logger.error(f"API key validation failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
    
    async def generate_image(self, prompt: str, model: str = None, size: str = None, 
                           count: int = None, quality: str = None, style: str = None) -> List[str]:
        """Enhanced image generation with caching and error handling."""
        if not await self.setup_api_key():
            return []
        
        # Use defaults if not specified
        model = model or Config.DEFAULT_IMG_MODEL
        size = size or Config.DEFAULT_IMG_SIZE
        count = min(count or Config.DEFAULT_IMG_COUNT, 4)
        quality = quality or Config.DEFAULT_IMG_QUALITY
        style = style or Config.DEFAULT_IMG_STYLE
        
        # Check cache first
        cache_key = f"{prompt}_{model}_{size}_{count}_{quality}_{style}"
        if self.cache and cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if time.time() - cached_result["timestamp"] < Config.CACHE_TTL:
                logger.info(f"Using cached result for: {prompt[:30]}...")
                return cached_result["urls"]
        
        # Check rate limit
        if not await API_MONITOR.check_rate_limit():
            logger.error("Rate limit exceeded for image generation")
            return []
        
        # Enhanced payload
        payload = {
            "model": model,
            "prompt": prompt,
            "n": count,
            "size": size,
            "response_format": "url",
            "quality": quality,
            "style": style
        }
        
        try:
            await API_MONITOR.record_request('image')
            
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            async with httpx.AsyncClient(timeout=Config.API_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/v1/images/generations",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    image_urls = [img["url"] for img in data.get("data", [])]
                    
                    # Cache the result
                    if self.cache:
                        self.cache[cache_key] = {
                            "urls": image_urls,
                            "timestamp": time.time()
                        }
                    
                    logger.info(f"Generated {len(image_urls)} images using model: {model}")
                    return image_urls
                else:
                    logger.error(f"Image generation error: {response.status_code} - {response.text}")
                    await API_MONITOR.record_error()
                    return []
                    
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            await API_MONITOR.record_error()
            return []
    
    async def get_available_models(self) -> List[Dict]:
        """Enhanced model listing with caching."""
        if not await self.setup_api_key():
            return []
        
        # Check cache
        cache_key = "models_list"
        if self.cache and cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if time.time() - cached_result["timestamp"] < 3600:  # Cache for 1 hour
                return cached_result["models"]
        
        try:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    
                    # Cache the result
                    if self.cache:
                        self.cache[cache_key] = {
                            "models": models,
                            "timestamp": time.time()
                        }
                    
                    return models
                else:
                    logger.error(f"Failed to get models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Models fetch error: {e}")
            return []
    
    async def enhance_prompt(self, prompt: str) -> str:
        """AI-powered prompt enhancement for better image generation."""
        try:
            enhancement_prompt = (
                f"Enhance this image generation prompt for better AI art results. "
                f"Make it more descriptive and detailed while keeping the original intent. "
                f"Return ONLY the enhanced prompt, no explanations.\n\n"
                f"Original: {prompt}"
            )
            
            ai = AIClient(enhancement_prompt)
            enhanced = await ai.get_response()
            
            if enhanced and not enhanced.startswith("⚠️"):
                logger.info(f"Prompt enhanced: '{prompt[:30]}...' -> '{enhanced[:30]}...'")
                return enhanced
            return prompt
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            return prompt
    
    def clear_cache(self):
        """Clear the image generation cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Image generation cache cleared")

class VoiceGenerator:
    """Enhanced Voice/Audio Generation for messages."""
    
    def __init__(self):
        self.api_key = Config.INFIP_API_KEY
        self.base_url = Config.INFIP_BASE_URL
        self.cache = {} if Config.CACHE_ENABLED else None
        
    async def generate_speech(self, text: str, voice: str = None, speed: float = None) -> Optional[str]:
        """Generate speech from text using TTS."""
        if not Config.ENABLE_VOICE_GENERATION:
            return None
            
        try:
            voice = voice or Config.DEFAULT_VOICE_MODEL
            speed = speed or Config.DEFAULT_VOICE_SPEED
            
            # Check cache
            cache_key = f"tts_{text}_{voice}_{speed}"
            if self.cache and cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if time.time() - cached_result["timestamp"] < Config.CACHE_TTL:
                    return cached_result["audio_url"]
            
            # Simulate TTS API call (replace with actual implementation)
            await asyncio.sleep(1.0)  # Simulate processing time
            
            # Mock audio URL (replace with real API call)
            audio_url = f"https://api.infip.pro/v1/audio/speech/{hash(text) % 10000}.mp3"
            
            # Cache result
            if self.cache:
                self.cache[cache_key] = {
                    "audio_url": audio_url,
                    "timestamp": time.time()
                }
            
            logger.info(f"Generated speech for: {text[:30]}...")
            return audio_url
            
        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            return None

class SmartReply:
    """Intelligent reply suggestion system."""
    
    def __init__(self):
        self.confidence_threshold = Config.SMART_REPLY_CONFIDENCE
        self.enabled = Config.ENABLE_SMART_REPLIES
        
    async def generate_reply(self, message_text: str, context: List[str] = None) -> Optional[Dict]:
        """Generate smart reply suggestions."""
        if not self.enabled:
            return None
            
        try:
            context_text = "\n".join(context[-5:]) if context else ""
            prompt = (
                f"Generate a natural, contextually appropriate reply to this message. "
                f"Keep it concise and conversational. Return JSON format: "
                f'{{"reply": "your reply", "confidence": 0.8, "tone": "casual"}}\n\n'
                f"Context: {context_text}\n"
                f"Message: {message_text}"
            )
            
            ai = AIClient(prompt)
            response = await ai.get_response()
            
            if response and not response.startswith("⚠️"):
                try:
                    import json
                    result = json.loads(response)
                    if result.get("confidence", 0) >= self.confidence_threshold:
                        return result
                except json.JSONDecodeError:
                    # Fallback to plain text
                    return {"reply": response, "confidence": 0.6, "tone": "casual"}
            
            return None
            
        except Exception as e:
            logger.error(f"Smart reply generation failed: {e}")
            return None

class ContentFilter:
    """Advanced content moderation and filtering."""
    
    def __init__(self):
        self.strictness = Config.CONTENT_FILTER_STRICTNESS
        self.enabled = Config.ENABLE_CONTENT_FILTER
        
    async def analyze_content(self, text: str) -> Dict:
        """Analyze content for inappropriate material."""
        if not self.enabled:
            return {"safe": True, "categories": {}, "confidence": 1.0}
            
        try:
            prompt = (
                f"Analyze this content for safety. Return JSON format: "
                f'{{"safe": true/false, "categories": {{"spam": 0.0, "toxicity": 0.0, "violence": 0.0}}, "confidence": 0.95}}\n\n'
                f"Text: {text}"
            )
            
            ai = AIClient(prompt)
            response = await ai.get_response()
            
            if response and not response.startswith("⚠️"):
                try:
                    import json
                    result = json.loads(response)
                    return self._apply_strictness(result)
                except json.JSONDecodeError:
                    return {"safe": True, "categories": {}, "confidence": 0.5}
            
            return {"safe": True, "categories": {}, "confidence": 0.5}
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {"safe": True, "categories": {}, "confidence": 1.0}
    
    def _apply_strictness(self, result: Dict) -> Dict:
        """Apply filtering strictness levels."""
        if self.strictness == "low":
            result["safe"] = True  # Allow most content
        elif self.strictness == "high":
            # Be more strict
            for category, score in result.get("categories", {}).items():
                if score > 0.3:
                    result["safe"] = False
                    break
        
        return result

class TranslationService:
    """Multi-language translation service."""
    
    def __init__(self):
        self.enabled = Config.ENABLE_AUTO_TRANSLATE
        self.source_lang = Config.DEFAULT_SOURCE_LANG
        self.target_lang = Config.DEFAULT_TARGET_LANG
        self.cache = {} if Config.CACHE_ENABLED else None
        
    async def translate(self, text: str, target_lang: str = None, source_lang: str = None) -> Optional[str]:
        """Translate text to target language."""
        if not self.enabled:
            return None
            
        try:
            target_lang = target_lang or self.target_lang
            source_lang = source_lang or self.source_lang
            
            # Check cache
            cache_key = f"trans_{source_lang}_{target_lang}_{hash(text)}"
            if self.cache and cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if time.time() - cached_result["timestamp"] < Config.CACHE_TTL:
                    return cached_result["translation"]
            
            prompt = (
                f"Translate this text from {source_lang} to {target_lang}. "
                f"Return ONLY the translated text, no explanations.\n\n"
                f"Text: {text}"
            )
            
            ai = AIClient(prompt)
            translation = await ai.get_response()
            
            if translation and not translation.startswith("⚠️"):
                # Cache result
                if self.cache:
                    self.cache[cache_key] = {
                        "translation": translation,
                        "timestamp": time.time()
                    }
                
                logger.info(f"Translated: {text[:30]}... -> {translation[:30]}...")
                return translation
            
            return None
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return None
    
    async def detect_language(self, text: str) -> Optional[str]:
        """Detect the language of the given text."""
        try:
            prompt = (
                f"Detect the language of this text. Return ONLY the ISO language code (e.g., 'en', 'es', 'fr').\n\n"
                f"Text: {text}"
            )
            
            ai = AIClient(prompt)
            lang_code = await ai.get_response()
            
            if lang_code and not lang_code.startswith("⚠️") and len(lang_code) == 2:
                return lang_code.lower()
            
            return None
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return None

class LearningSystem:
    """Continuous learning and adaptation system."""
    
    def __init__(self):
        self.enabled = Config.ENABLE_CONTINUOUS_LEARNING
        self.batch_size = Config.LEARNING_BATCH_SIZE
        self.learning_data = []
        
    async def learn_from_interaction(self, user_input: str, ai_response: str, feedback: str = None):
        """Learn from user interactions."""
        if not self.enabled:
            return
            
        try:
            learning_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "ai_response": ai_response,
                "feedback": feedback,
                "context": "conversation"
            }
            
            self.learning_data.append(learning_entry)
            
            # Process batch when full
            if len(self.learning_data) >= self.batch_size:
                await self._process_learning_batch()
                
        except Exception as e:
            logger.error(f"Learning system error: {e}")
    
    async def _process_learning_batch(self):
        """Process a batch of learning data."""
        if not self.learning_data:
            return
            
        try:
            # Create learning summary
            batch_summary = "\n".join([
                f"User: {entry['user_input']}\nAI: {entry['ai_response']}\nFeedback: {entry.get('feedback', 'None')}\n"
                for entry in self.learning_data[-10:]  # Last 10 entries
            ])
            
            prompt = (
                f"Analyze these conversation excerpts and identify patterns for improvement. "
                f"Return JSON format: {{'improvements': ['suggestion1', 'suggestion2'], 'patterns': ['pattern1', 'pattern2']}}\n\n"
                f"{batch_summary}"
            )
            
            ai = AIClient(prompt)
            insights = await ai.get_response()
            
            if insights and not insights.startswith("⚠️"):
                logger.info(f"Learning insights: {insights}")
            
            # Clear processed data
            self.learning_data = []
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")

# Initialize new feature instances
VOICE_GEN = VoiceGenerator()
SMART_REPLY = SmartReply()
CONTENT_FILTER = ContentFilter()
TRANSLATOR = TranslationService()
LEARNING_SYSTEM = LearningSystem()

# =================================================================================================
# ☁️ CLOUD SERVICES (IMAGE & AI)
# =================================================================================================

class ImageUploader:
    """Handles uploading images to ImgBB for AI Vision."""
    def __init__(self):
        self.url = "https://api.imgbb.com/1/upload"
        self.params = {"key": Config.IMGBB_KEY, "expiration": 600}

    async def upload(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path): 
            logger.error(f"File not found: {file_path}")
            return None
        
        # Check rate limit before upload
        if not await API_MONITOR.check_rate_limit():
            logger.error("Rate limit exceeded for image upload")
            return None
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                await API_MONITOR.record_request('image')
                
                with open(file_path, "rb") as img:
                    async with httpx.AsyncClient(timeout=Config.API_TIMEOUT) as client:
                        response = await client.post(self.url, params=self.params, files={"image": img})
                        if response.status_code == 200:
                            data = response.json()
                            url = data.get("data", {}).get("url")
                            if url:
                                logger.info(f"Image uploaded successfully: {url[:50]}...")
                                return url
                        else:
                            logger.error(f"ImgBB API Error: {response.status_code} - {response.text}")
                            await API_MONITOR.record_error()
            except httpx.TimeoutException:
                logger.error(f"ImgBB Upload Timeout (attempt {attempt + 1})")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
            except httpx.RequestError as e:
                logger.error(f"ImgBB Network Error (attempt {attempt + 1}): {e}")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
            except IOError as e:
                logger.error(f"ImgBB File Error: {e}")
                await API_MONITOR.record_error()
                break
            except Exception as e:
                logger.error(f"ImgBB Upload Error (attempt {attempt + 1}): {e}")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
        return None

class AIClient:
    """Core Client to fetch AI responses with Vision support."""
    def __init__(self, prompt: str, image_urls: List[str] = None):
        self.prompt = prompt
        self.image_urls = image_urls or []

    async def get_response(self) -> str:
        files_payload = []
        for url in self.image_urls:
            files_payload.append({'url': url, 'mimeType': 'image/jpeg', 'name': 'image.jpg'})

        payload = {
            'stream': True,
            'message': {
                'role': 'user',
                'content': self.prompt,
                'files': files_payload
            },
            'product': 'ai-chat',
            'prompt': {'id': 'ai_chat'},
            'tools': [],
        }

        # Check rate limit before API call
        if not await API_MONITOR.check_rate_limit():
            return "⚠️ <b>Error:</b> Rate limit exceeded. Please wait before making more requests."

        for attempt in range(Config.MAX_RETRIES):
            try:
                await API_MONITOR.record_request('ai')
                
                async with httpx.AsyncClient(cookies=Config.AUTH_COOKIES, headers=Config.AUTH_HEADERS, timeout=Config.API_TIMEOUT) as client:
                    response = await client.post(
                        'https://quillbot.com/api/raven/quill-chat/responses',
                        json=payload
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"AI API Error: {response.status_code} - {response.text}")
                        await API_MONITOR.record_error()
                        if response.status_code == 429:  # Rate limit
                            return "⚠️ <b>Error:</b> API rate limit exceeded. Please wait."
                        elif response.status_code >= 500:
                            if attempt < Config.MAX_RETRIES - 1:
                                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
                                continue
                        return "⚠️ <b>Error:</b> AI service unavailable."
                    
                    full_text = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: {") and '"chunk":"' in line:
                            try:
                                json_str = line[6:]
                                data_obj = json.loads(json_str)
                                full_text += data_obj.get("chunk", "")
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                logger.warning(f"Chunk parsing error: {e}")
                                continue
                    
                    if not full_text.strip():
                        logger.warning("Empty AI response received")
                        await API_MONITOR.record_error()
                        return "⚠️ <b>Error:</b> Empty response from AI."
                    
                    logger.info(f"AI response generated successfully ({len(full_text)} chars)")
                    return self.clean_text(full_text)
                    
            except httpx.TimeoutException:
                logger.error(f"AI API Timeout (attempt {attempt + 1})")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
            except httpx.RequestError as e:
                logger.error(f"AI API Network Error (attempt {attempt + 1}): {e}")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
            except Exception as e:
                logger.error(f"AI API Error (attempt {attempt + 1}): {e}")
                await API_MONITOR.record_error()
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
        
        return "⚠️ <b>Error:</b> Neural Link Severed. Check cookies."

    @staticmethod
    def clean_text(text: str) -> str:
        if not text: return ""
        text = text.replace("\\(", "").replace("\\)", "")
        text = text.replace("\\[", "").replace("\\]", "")
        text = re.sub(r'\\([a-zA-Z])', r'\1', text)
        return text.strip()

# =================================================================================================
# 💾 DATA & STATE MANAGEMENT
# =================================================================================================

class GemManager:
    def __init__(self):
        self.db_name = Config.DB_NAME
        self.dm_mode_active = False
        self.active_dm_gem = None
        self._db_lock = asyncio.Lock()
        
        # --- STATE STORE ---
        self.active_chats = {} 
        self.active_targets = {}
        self.global_stalk_targets = {} 
        
        self.default_persona = (
            "You are a witty, slightly sarcastic but helpful human user. "
            "You are chatting on Telegram. Keep responses short, casual, and lower-case if appropriate. "
            "Do not act like a robotic assistant. Recall details from the Chat History provided."
        )

    async def ensure_db(self):
        """Ensure database tables exist with proper error handling."""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute("CREATE TABLE IF NOT EXISTS gems (name TEXT PRIMARY KEY, content TEXT)")
                await db.commit()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    async def create_gem(self, name: str, content: str):
        """Create or update a gem with input validation."""
        if not name or not name.strip():
            raise ValueError("Gem name cannot be empty")
        if not content or not content.strip():
            raise ValueError("Gem content cannot be empty")
            
        name = name.strip().lower()
        content = content.strip()
        
        async with self._db_lock:
            try:
                await self.ensure_db()
                async with aiosqlite.connect(self.db_name) as db:
                    await db.execute("INSERT OR REPLACE INTO gems (name, content) VALUES (?, ?)", (name, content))
                    await db.commit()
                    logger.info(f"Gem '{name}' created/updated successfully")
            except Exception as e:
                logger.error(f"Failed to create gem '{name}': {e}")
                raise

    async def get_gem(self, name: str) -> Optional[str]:
        """Retrieve a gem by name with proper error handling."""
        if not name or not name.strip():
            return None
            
        name = name.strip().lower()
        
        try:
            await self.ensure_db()
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute("SELECT content FROM gems WHERE name = ?", (name,))
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get gem '{name}': {e}")
            return None
            
    async def delete_gem(self, name: str) -> bool:
        """Delete a gem by name with validation."""
        if not name or not name.strip():
            return False
            
        name = name.strip().lower()
        
        async with self._db_lock:
            try:
                await self.ensure_db()
                async with aiosqlite.connect(self.db_name) as db:
                    cursor = await db.execute("DELETE FROM gems WHERE name = ?", (name,))
                    await db.commit()
                    deleted = cursor.rowcount > 0
                    if deleted:
                        logger.info(f"Gem '{name}' deleted successfully")
                    return deleted
            except Exception as e:
                logger.error(f"Failed to delete gem '{name}': {e}")
                return False

    async def list_gems(self) -> List[str]:
        """List all gems with error handling."""
        try:
            await self.ensure_db()
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute("SELECT name FROM gems ORDER BY name")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to list gems: {e}")
            return []

    def add_history(self, context_dict, role, content):
        if "history" not in context_dict: context_dict["history"] = []
        # Timestamping for better AI time-awareness
        timestamp = datetime.now().strftime("%H:%M")
        context_dict["history"].append(f"[{timestamp}] {role}: {content}")
        
        if len(context_dict["history"]) > Config.MAX_HISTORY_DEPTH:
            context_dict["history"] = context_dict["history"][-Config.MAX_HISTORY_DEPTH:]

    def build_prompt(self, system_prompt, history, current_input):
        hist_text = "\n".join(history)
        return (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
            f"--- CONVERSATION MEMORY ---\n{hist_text}\n"
            f"---------------------------\n"
            f"LATEST MESSAGE: {current_input}\n"
            f"YOUR REPLY:"
        )

GEMS = GemManager()

# =================================================================================================
# 🎭 HUMAN BEHAVIOR MIMICRY ENGINE
# =================================================================================================

class HumanBehavior:
    """Handles the timing and actions to make the bot feel alive."""
    
    @staticmethod
    async def simulate_reading(client: Client, chat_id: int, text: str, is_image: bool = False):
        """
        Simulates:
        1. Seeing the notification (random delay)
        2. Marking as read (Blue ticks)
        3. Reading/Downloading time
        """
        if not text and not is_image:
            return
            
        try:
            # Reaction time (0.5s to 2.5s)
            await asyncio.sleep(random.uniform(0.5, 2.5))
            
            # Mark as Read (Crucial for human feel)
            try:
                await client.read_chat_history(chat_id)
            except Exception as e:
                logger.warning(f"Failed to mark chat as read: {e}")

            # "Reading" or "Downloading" time
            if is_image:
                try:
                    await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_PHOTO)
                except Exception as e:
                    logger.warning(f"Failed to send upload action: {e}")
                await asyncio.sleep(random.uniform(1.5, 3.0)) # Fake staring at image
            else:
                # Approx 0.05s per character + base thinking time
                read_delay = min(len(text) * 0.05, 4.0)
                await asyncio.sleep(read_delay)
        except Exception as e:
            logger.error(f"Error in simulate_reading: {e}")

    @staticmethod
    async def simulate_typing(client: Client, chat_id: int, response_text: str):
        """
        Simulates natural typing speed with variations.
        Average typing speed: ~60 WPM => ~5 chars/sec
        """
        if not response_text: return
        
        try:
            # Calculate base duration
            char_count = len(response_text)
            # Random speed between 5 to 9 chars per second
            typing_speed = random.uniform(5.0, 9.0) 
            duration = char_count / typing_speed
            
            # Cap duration so we don't type for 2 minutes for a paragraph
            duration = min(duration, 10.0) 

            # If very short (e.g., "ok"), type fast.
            if duration < 1.0: duration = 1.0

            try:
                await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
            except Exception as e:
                logger.warning(f"Failed to send typing action: {e}")
            await asyncio.sleep(duration)
        except Exception as e:
            logger.error(f"Error in simulate_typing: {e}")

# =================================================================================================
#  API MANAGEMENT COMMANDS
# =================================================================================================

@Client.on_message(filters.command("api", prefix) & filters.me)
async def api_management_handler(client: Client, message: Message):
    args = message.text.split(" ", 2)
    cmd = args[1].lower() if len(args) > 1 else "status"
    
    if cmd == "status":
        stats = API_MONITOR.get_stats()
        
        # UI: Visual Progress Bars
        min_bar = UIHelper.progress_bar(stats['requests_per_minute'], Config.MAX_REQUESTS_PER_MINUTE)
        hr_bar = UIHelper.progress_bar(stats['requests_per_hour'], Config.MAX_REQUESTS_PER_HOUR)
        
        msg = (
            f"<b>📊 API Status Report</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>📈 Current Load:</b>\n"
            f"• 1m: <code>{min_bar}</code> ({stats['requests_per_minute']}/{Config.MAX_REQUESTS_PER_MINUTE})\n"
            f"• 1h: <code>{hr_bar}</code> ({stats['requests_per_hour']}/{Config.MAX_REQUESTS_PER_HOUR})\n\n"
            f"<b>📅 Daily Stats:</b>\n"
            f"• AI Requests: {stats['daily_ai_requests']}\n"
            f"• Image Uploads: {stats['daily_image_uploads']}\n"
            f"• Errors: {stats['daily_errors']}\n\n"
            f"<b>⚙️ Config:</b>\n"
            f"• Timeout: {Config.API_TIMEOUT}s | Retries: {Config.MAX_RETRIES}"
        )
        await edit_ui(message, "API Status", msg, parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "health":
        await message.edit("🔍 <b>Checking API Health...</b>", parse_mode=enums.ParseMode.HTML)
        
        health_status = []
        
        # Test AI API
        try:
            test_ai = AIClient("Respond with 'OK' only.")
            response = await test_ai.get_response()
            if "OK" in response:
                health_status.append("✅ AI API: Healthy")
            else:
                health_status.append(f"⚠️ AI API: Unexpected response")
        except Exception as e:
            health_status.append(f"❌ AI API: {str(e)[:50]}...")
        
        # Test Image Upload
        try:
            # Create a small test image
            import io
            from PIL import Image
            
            test_img = Image.new('RGB', (100, 100), color='red')
            test_bytes = io.BytesIO()
            test_img.save(test_bytes, format='JPEG')
            test_bytes.seek(0)
            
            # Save temporarily
            test_path = "test_health_check.jpg"
            with open(test_path, "wb") as f:
                f.write(test_bytes.getvalue())
            
            uploader = ImageUploader()
            result = await uploader.upload(test_path)
            
            if result:
                health_status.append("✅ Image Upload: Healthy")
            else:
                health_status.append("❌ Image Upload: Failed")
            
            # Cleanup
            if os.path.exists(test_path):
                os.remove(test_path)
                
        except ImportError:
            health_status.append("⚠️ Image Upload: PIL not available")
        except Exception as e:
            health_status.append(f"❌ Image Upload: {str(e)[:50]}...")
        
        # Rate Limit Status
        rate_limited = not await API_MONITOR.check_rate_limit()
        if rate_limited:
            health_status.append("⚠️ Rate Limit: Active")
        else:
            health_status.append("✅ Rate Limit: Clear")
        
        await edit_ui(message, "API Health Check", "\n".join(health_status))
    
    elif cmd == "reset":
        if len(args) < 3:
            return await edit_ui(message, "Usage", ".api reset <daily|hour|minute>")
        
        reset_type = args[2].lower()
        async with API_MONITOR._lock:
            if reset_type == "daily":
                API_MONITOR.daily_usage = {
                    'ai_requests': 0,
                    'image_uploads': 0,
                    'errors': 0,
                    'last_reset': datetime.now().date()
                }
                await edit_ui(message, "✅ Reset", "Daily usage statistics reset.")
            elif reset_type == "hour":
                API_MONITOR.hourly_requests = []
                await edit_ui(message, "✅ Reset", "Hourly usage statistics reset.")
            elif reset_type == "minute":
                API_MONITOR.request_times = []
                await edit_ui(message, "✅ Reset", "Minute usage statistics reset.")
            else:
                await edit_ui(message, "Error", "Invalid reset type. Use: daily, hour, minute")
    
    elif cmd == "config":
        if len(args) < 4:
            return await edit_ui(message, "Usage", ".api config <key> <value>")
        
        key = args[2].lower()
        value = args[3]
        
        try:
            if key in ["max_retries", "retry_delay"]:
                setattr(Config, key.upper(), int(value))
                await edit_ui(message, "✅ Config Updated", f"{key} = {value}")
            elif key == "api_timeout":
                setattr(Config, key.upper(), float(value))
                await edit_ui(message, "✅ Config Updated", f"{key} = {value}s")
            elif key in ["max_requests_per_minute", "max_requests_per_hour"]:
                setattr(Config, key.upper(), int(value))
                await edit_ui(message, "✅ Config Updated", f"{key} = {value}")
            else:
                await edit_ui(message, "Error", f"Unknown config key: {key}")
        except ValueError:
            await edit_ui(message, "Error", "Invalid value type.")
    
    else:
        help_text = (
            "<b>🔧 API Management Commands:</b>\n\n"
            "• <code>.api status</code> - Show usage statistics\n"
            "• <code>.api health</code> - Check API health\n"
            "• <code>.api reset <type></code> - Reset usage stats\n"
            "• <code>.api config <key> <value></code> - Update config\n\n"
            "<b>Reset types:</b> daily, hour, minute\n"
            "<b>Config keys:</b> max_retries, retry_delay, api_timeout, max_requests_per_minute, max_requests_per_hour"
        )
        await edit_ui(message, "API Management", help_text, parse_mode=enums.ParseMode.HTML)

# =================================================================================================
#  GEM COMMANDS
# =================================================================================================

async def edit_ui(message: Message, header: str, content: str, parse_mode=enums.ParseMode.HTML):
    """Helper to send pretty messages with proper error handling."""
    if not message:
        logger.error("Message object is None in edit_ui")
        return
        
    try:
        text = f"<b>{html.escape(header)}</b>\n\n{content}"
        await message.edit(text, parse_mode=parse_mode)
    except Exception as e:
        try:
            # Fallback to plain text/raw if parse mode fails
            text = f"{header}\n\n{content}"
            await message.edit(text, parse_mode=enums.ParseMode.DISABLED)
        except Exception as fallback_e:
            logger.error(f"Failed to edit message in both formats: {e}, {fallback_e}")

@Client.on_message(filters.command("gem", prefix) & filters.me)
async def gem_handler(client: Client, message: Message):
    args = message.text.split(" ", 2)
    cmd = args[1].lower() if len(args) > 1 else "help"
    
    await GEMS.ensure_db()

    # --- GEM LEARN (DEEP HISTORY ANALYSIS) ---
    if cmd == "learn":
        # Usage: .gem learn <@user/reply> [msg_limit]
        target_user = None
        limit = 100 # Default scrape limit
        
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            if len(args) > 2 and args[2].isdigit():
                limit = int(args[2])
        elif len(args) > 2:
            try:
                potential_user = args[2].split()[0]
                target_user = await client.get_users(potential_user)
                if len(args[2].split()) > 1 and args[2].split()[1].isdigit():
                    limit = int(args[2].split()[1])
            except Exception as e:
                return await edit_ui(message, "Error", f"User not found: {e}")

        if not target_user:
            return await edit_ui(message, "Usage", "Reply to user or use: <code>.gem learn @user [limit]</code>")

        await message.edit(f"🧠 <b>Studying {target_user.first_name}...</b>\nReading last {limit} messages.", parse_mode=enums.ParseMode.HTML)

        collected_text = ""
        msg_count = 0
        
        # Scrape History
        try:
            async for history_msg in client.get_chat_history(message.chat.id, limit=limit):
                if history_msg.from_user and history_msg.from_user.id == target_user.id:
                    content = history_msg.text or history_msg.caption
                    if content:
                        collected_text += f"{content}\n"
                        msg_count += 1
        except Exception as e:
            return await edit_ui(message, "Error", f"Failed to fetch history: {e}")

        if not collected_text:
            return await edit_ui(message, "Error", "No text messages found for this user in the fetch limit.")

        # Truncate to avoid token overflow
        collected_text = collected_text[:4000]

        await message.edit(f"🧪 <b>Synthesizing Persona...</b>\nAnalyzing {msg_count} messages.", parse_mode=enums.ParseMode.HTML)

        # The "Deep Learn" Prompt
        prompt = (
            f"You are an expert linguistic profiler. Below is a dataset of chat messages from a user named {target_user.first_name}.\n\n"
            f"DATASET:\n{collected_text}\n\n"
            f"TASK: Create a highly detailed 'System Prompt' (Instruction) for an AI that forces it to act exactly like this user.\n"
            f"1. Analyze their tone (sarcastic, cute, rude, formal, etc).\n"
            f"2. Analyze their sentence structure (lowercase, capitalization, punctuation usage).\n"
            f"3. Note their slang and emoji usage.\n"
            f"4. The output must be the raw System Prompt only. Do not add introductory text."
        )

        ai = AIClient(prompt)
        result = await ai.get_response()
        
        gem_name = f"clone_{target_user.first_name.lower().replace(' ', '')[:8]}"
        await GEMS.create_gem(gem_name, result)
        
        await edit_ui(message, "🧬 Deep Clone Created", 
                      f"<b>Name:</b> <code>{gem_name}</code>\n"
                      f"<b>Source:</b> {msg_count} messages analyzed.\n\n"
                      f"<i>Use <code>.gem use {gem_name}</code> to become them.</i>")

    # --- GENERATE GEM (AI) ---
    elif cmd == "gen":
        if len(args) < 3: return await edit_ui(message, "Usage", ".gem gen <topic>")
        await message.edit("🔮 <b>Forging Persona...</b>", parse_mode=enums.ParseMode.HTML)
        
        prompt = f"Create a System Prompt for an AI to act as: {args[2]}. Return ONLY the prompt text."
        ai = AIClient(prompt)
        result = await ai.get_response()
        
        gem_name = args[2].split()[0].lower() + "_ai"
        await GEMS.create_gem(gem_name, result)
        await edit_ui(message, "✨ Gem Created", f"<b>Name:</b> <code>{gem_name}</code>\n\n{html.escape(result[:100])}...")

    # --- ANALYZE USER (AI - Single Message) ---
    elif cmd == "analyze":
        if not message.reply_to_message: return await edit_ui(message, "Error", "Reply to a user.")
        await message.edit("🕵️ <b>Analyzing Personality...</b>", parse_mode=enums.ParseMode.HTML)
        
        reply = message.reply_to_message
        txt = reply.text or reply.caption or "Image/Media"
        name = reply.from_user.first_name if reply.from_user else "Unknown"
        
        prompt = f"Analyze this user message ({name}): '{txt}'. Create a System Prompt to mimic them. Return ONLY prompt."
        ai = AIClient(prompt)
        result = await ai.get_response()
        
        gem_name = f"mimic_{name.lower()[:5]}"
        await GEMS.create_gem(gem_name, result)
        await edit_ui(message, "🧬 Clone Created", f"<b>Name:</b> <code>{gem_name}</code>\n\n{html.escape(result[:100])}...")

    # --- MANUAL CREATION (REQUESTED) ---
    elif cmd == "create":
        # Syntax: .gem create gem_name The prompt goes here
        if len(args) < 3: 
            return await edit_ui(message, "Usage", "<code>.gem create <name> <content></code>")
        
        payload = args[2].split(" ", 1)
        if len(payload) < 2:
            return await edit_ui(message, "Error", "Content missing. Format:\n<code>.gem create name prompt text...</code>")
        
        gem_name = payload[0]
        gem_content = payload[1]
        
        await GEMS.create_gem(gem_name, gem_content)
        await edit_ui(message, "💾 Gem Saved", f"<b>Gem Name:</b> <code>{gem_name}</code>\n<b>Length:</b> {len(gem_content)} chars")
    
    # --- DELETE GEM ---
    elif cmd == "delete":
        if len(args) < 3: return await edit_ui(message, "Usage", ".gem delete <name>")
        gem_name = args[2].lower()
        success = await GEMS.delete_gem(gem_name)
        if success:
            await edit_ui(message, "🗑️ Gem Deleted", f"<b>{gem_name}</b> has been destroyed.")
        else:
            await edit_ui(message, "Error", f"Gem <b>{gem_name}</b> not found.")

    # --- LIST GEMS (REQUESTED) ---
    elif cmd == "list":
        gems = await GEMS.list_gems()
        if gems:
            # Formatting the list beautifully
            gem_list_str = "\n".join([f"💎 <code>{g}</code>" for g in sorted(gems)])
            count = len(gems)
            await edit_ui(message, f"📚 Gem Collection ({count})", gem_list_str)
        else:
            await edit_ui(message, "📚 Gem Collection", "The vault is empty.\nUse <code>.gem create</code> or <code>.gem gen</code>.")

    # --- SET DM GEM ---
    elif cmd == "use":
        if len(args) < 3: return await edit_ui(message, "Usage", ".gem use <name>")
        content = await GEMS.get_gem(args[2])
        if content:
            GEMS.active_dm_gem = content
            await edit_ui(message, "✅ DM Gem Set", f"Using <b>{args[2]}</b> for DMs.")
        else:
            await edit_ui(message, "❌ Error", "Gem not found.")
            
    else:
        await edit_ui(message, "Gem System", "Commands:\nlearn, gen, analyze, create, delete, list, use")

# =================================================================================================
# 🛡️ API ERROR RECOVERY SYSTEM
# =================================================================================================

class APIRecoveryManager:
    """Manages API error recovery and fallback mechanisms."""
    
    def __init__(self):
        self.consecutive_errors = 0
        self.last_error_time = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.fallback_responses = [
            "I'm having trouble connecting right now. Please try again in a moment.",
            "Sorry, I'm experiencing technical difficulties. Let's try again later.",
            "Connection issues detected. Please give me a moment to recover."
        ]
    
    async def handle_error(self, error_type: str) -> Optional[str]:
        """Handle API errors and determine if circuit breaker should be triggered."""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        logger.warning(f"API Error #{self.consecutive_errors}: {error_type}")
        
        # Trigger circuit breaker if too many consecutive errors
        if self.consecutive_errors >= self.circuit_breaker_threshold:
            logger.error("Circuit breaker triggered - API temporarily disabled")
            return "⚠️ <b>Error:</b> API temporarily unavailable due to repeated failures. Please wait a few minutes."
        
        # Return fallback response
        return random.choice(self.fallback_responses)
    
    async def handle_success(self):
        """Reset error counters on successful API call."""
        if self.consecutive_errors > 0:
            logger.info(f"API recovered after {self.consecutive_errors} errors")
        self.consecutive_errors = 0
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        if self.consecutive_errors >= self.circuit_breaker_threshold:
            # Check if timeout has passed
            if time.time() - self.last_error_time > self.circuit_breaker_timeout:
                return False  # Circuit can be reset
            return True  # Circuit is still open
        return False

RECOVERY_MANAGER = APIRecoveryManager()

# =================================================================================================
# 🧠 AI CONTROL (GAI) COMMANDS
# =================================================================================================

@Client.on_message(filters.command("gai", prefix) & filters.me)
async def ai_control_handler(client: Client, message: Message):
    args = message.text.split(" ", 2)
    cmd = args[1].lower() if len(args) > 1 else "ask"
    
    # --- 1. QUICK ASK (ONE-SHOT) ---
    if cmd not in ["dm", "chat", "bot", "stalk", "stop", "wipe", "status", "summary"]:
        # Case: .gai Why is the sky blue?
        query = args[1] if len(args) > 1 else ""
        
        # Handle Reply Context
        reply_ctx = ""
        img_url = []
        
        if message.reply_to_message:
            r = message.reply_to_message
            reply_ctx = f"Context Message: {r.text or r.caption or ''}\n"
            if r.photo:
                await message.edit("👁️ <b>Downloading Image...</b>", parse_mode=enums.ParseMode.HTML)
                path = await client.download_media(r.photo)
                uploader = ImageUploader()
                url = await uploader.upload(path)
                if url: img_url.append(url)
                if os.path.exists(path): os.remove(path)
        
        # Check circuit breaker before making API call
        if RECOVERY_MANAGER.is_circuit_open():
            return await edit_ui(message, "Circuit Breaker", "⚠️ <b>API temporarily disabled</b>\n\nToo many consecutive errors detected.\nPlease wait a few minutes before trying again.")
        
        if not query and not reply_ctx:
            return await edit_ui(message, "AI Tool", "Use <code>.gai <question></code> or reply to a message.")

        await message.edit("🧠 <b>Thinking...</b>", parse_mode=enums.ParseMode.HTML)
        
        full_prompt = f"{reply_ctx}\nUser Question: {query}"
        ai = AIClient(full_prompt, image_urls=img_url)
        resp = await ai.get_response()
        
        # Check if response indicates an error
        if resp.startswith("⚠️"):
            fallback = await RECOVERY_MANAGER.handle_error("AI_API_ERROR")
            if fallback:
                resp = fallback
        else:
            await RECOVERY_MANAGER.handle_success()
        
        # Robust Sending (Fixes parse_mode errors)
        try:
            await message.edit(resp, parse_mode=enums.ParseMode.MARKDOWN)
        except Exception:
            try:
                await message.edit(html.escape(resp), parse_mode=enums.ParseMode.HTML)
            except Exception:
                await message.edit(resp, parse_mode=enums.ParseMode.DISABLED)
        return

    sub_args = args[2].split() if len(args) > 2 else []

    # --- 2. MODES ---
    
    if cmd == "dm": # Toggle DM Auto-Reply
        state = sub_args[0].lower() if sub_args else "status"
        if state == "on": GEMS.dm_mode_active = True
        elif state == "off": GEMS.dm_mode_active = False
        await edit_ui(message, "📨 DM Auto-Pilot", f"Status: <b>{'ON' if GEMS.dm_mode_active else 'OFF'}</b>")

    elif cmd == "chat": # Target Current Chat
        chat_id = message.chat.id
        gem_name = sub_args[0] if sub_args else "default"
        
        content = await GEMS.get_gem(gem_name) or GEMS.default_persona
        GEMS.active_chats[chat_id] = {"gem": content, "history": []}
        await edit_ui(message, "⚔️ Chat Agent Active", f"Gem: <b>{gem_name}</b>\nI will reply to everyone here.")

    elif cmd == "bot": # Target Specific Bot in Current Chat
        if not sub_args: return await edit_ui(message, "Usage", ".gai bot @user [gem]")
        try:
            target = await client.get_users(sub_args[0])
            gem_name = sub_args[1] if len(sub_args) > 1 else "default"
            content = await GEMS.get_gem(gem_name) or GEMS.default_persona
            
            GEMS.active_targets[target.id] = {"gem": content, "history": []}
            await edit_ui(message, "🤖 Bot Target Locked", f"Target: {target.first_name}\nGem: <b>{gem_name}</b>\n(Active in this chat only)")
        except Exception as e:
            await edit_ui(message, "Error", str(e))

    elif cmd == "stalk": # Global Stalker
        if not sub_args: return await edit_ui(message, "Usage", ".gai stalk @user [gem]")
        try:
            target = await client.get_users(sub_args[0])
            gem_name = sub_args[1] if len(sub_args) > 1 else "default"
            content = await GEMS.get_gem(gem_name) or GEMS.default_persona
            
            GEMS.global_stalk_targets[target.id] = {"gem": content, "history": []}
            await edit_ui(message, "🌍 Global Stalker", f"Target: {target.first_name}\nGem: <b>{gem_name}</b>\n\nI will reply to them <b>EVERYWHERE</b> I see them.")
        except Exception as e:
            await edit_ui(message, "Error", str(e))

    elif cmd == "stop": # Stop actions
        # --- NEW: STOP ALL FUNCTIONALITY ---
        if sub_args and sub_args[0].lower() == "all":
            GEMS.dm_mode_active = False
            GEMS.active_chats.clear()
            GEMS.active_targets.clear()
            GEMS.global_stalk_targets.clear()
            await edit_ui(message, "☢️ KILL SWITCH", "<b>ALL AI SYSTEMS SHUT DOWN.</b>\n\n• DM Mode: OFF\n• Group Chats: 0\n• Targets: 0\n• Stalkers: 0")
        else:
            # Default: Stop current chat only
            cid = message.chat.id
            wiped = []
            if cid in GEMS.active_chats:
                del GEMS.active_chats[cid]
                wiped.append("Current Chat")
            
            await edit_ui(message, "🛑 AI Stopped", f"Stopped in: {', '.join(wiped) or 'No active sessions here.'}\n\n<i>To stop everything, use:</i> <code>.gai stop all</code>")

    elif cmd == "wipe": # Clear History
        cid = message.chat.id
        if cid in GEMS.active_chats:
            GEMS.active_chats[cid]["history"] = []
            await edit_ui(message, "🧠 Memory Wiped", "Chat history cleared.")
        else:
            await edit_ui(message, "Info", "AI not active here.")

    elif cmd == "status": # Detailed Stats
        msg = "<b>📊 AI System Status</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"<b>📨 DM Mode:</b> {'✅ ON' if GEMS.dm_mode_active else '❌ OFF'}\n\n"
        
        msg += "<b>⚔️ Active Chats:</b>\n"
        if not GEMS.active_chats: msg += "• None\n"
        for cid, data in GEMS.active_chats.items():
            msg += f"• ID: <code>{cid}</code> | Hist: {len(data['history'])}\n"
            
        msg += "\n<b>🤖 Local Targets:</b>\n"
        if not GEMS.active_targets: msg += "• None\n"
        for uid in GEMS.active_targets:
            msg += f"• User ID: <code>{uid}</code>\n"

        msg += "\n<b>🌍 Global Stalkers:</b>\n"
        if not GEMS.global_stalk_targets: msg += "• None\n"
        for uid in GEMS.global_stalk_targets:
            msg += f"• User ID: <code>{uid}</code>\n"
            
        await edit_ui(message, "Status Report", msg)

    elif cmd == "summary": # Summarizer Tool
        limit = int(sub_args[0]) if sub_args else 50
        await message.edit(f"📝 <b>Reading last {limit} messages...</b>", parse_mode=enums.ParseMode.HTML)
        
        history_text = ""
        async for msg in client.get_chat_history(message.chat.id, limit=limit):
            if msg.text or msg.caption:
                name = msg.from_user.first_name if msg.from_user else "Unknown"
                content = msg.text or msg.caption
                history_text = f"{name}: {content}\n" + history_text
        
        if not history_text: return await edit_ui(message, "Error", "No text found to summarize.")
        
        prompt = (
            f"Summarize the following Telegram chat conversation in bullet points. "
            f"Highlight key topics and funny moments.\n\n{history_text}"
        )
        ai = AIClient(prompt)
        res = await ai.get_response()
        await edit_ui(message, "📝 Chat Summary", res)

# =================================================================================================
# 🎨 IMAGE GENERATION COMMANDS
# =================================================================================================

IMG_GEN = ImageGenerator()

@Client.on_message(filters.command("img", prefix) & filters.me)
async def image_generation_handler(client: Client, message: Message):
    """Handle enhanced image generation commands."""
    args = message.text.split(" ", 2)
    cmd = args[1].lower() if len(args) > 1 else "help"
    
    if cmd == "gen":
        # Usage: .img gen A beautiful sunset over mountains
        if len(args) < 3:
            return await edit_ui(message, "Usage", "<code>.img gen [prompt]</code>\n\nExample: <code>.img gen A futuristic city at sunset</code>", parse_mode=enums.ParseMode.HTML)
        
        prompt = args[2]
        await message.edit("🎨 <b>Generating Image...</b>\nPlease wait...", parse_mode=enums.ParseMode.HTML)
        
        # Generate image
        image_urls = await IMG_GEN.generate_image(prompt)
        
        if image_urls:
            # Send first image
            try:
                await message.delete()
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=image_urls[0],
                    # ESCAPE prompt to prevent HTML injection errors
                    caption=f"🎨 <b>Generated Image</b>\n\n<b>Prompt:</b> {html.escape(prompt)}\n<b>Model:</b> {Config.DEFAULT_IMG_MODEL}",
                    parse_mode=enums.ParseMode.HTML
                )
                
                # Send additional images if any
                for url in image_urls[1:]:
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=url,
                        caption="🎨 Additional variation",
                        parse_mode=enums.ParseMode.HTML
                    )
                    
            except Exception as e:
                logger.error(f"Failed to send generated image: {e}")
                await edit_ui(message, "Error", f"Generated image but failed to send: {e}", parse_mode=enums.ParseMode.HTML)
        else:
            await edit_ui(message, "Error", "❌ Failed to generate image. Please try again later.", parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "surprise":
        # Check if a specific topic was provided for the surprise
        # Usage: .img surprise [topic]
        topic_instruction = ""
        topic_text = ""
        if len(args) > 2:
            topic_text = args[2]
            topic_instruction = f" based on the topic: '{topic_text}'"
            
        await message.edit(f"🎲 <b>Dreaming up a{' ' + topic_text if topic_text else ' random'} concept...</b>", parse_mode=enums.ParseMode.HTML)
        
        # 1. Generate a prompt using AI
        creation_prompt = (
            f"Generate a highly detailed, creative, and unique prompt for an AI image generator{topic_instruction}. "
            "Focus on visual descriptions, lighting, atmosphere, and artistic style. Return ONLY the prompt text descriptions."
        )
        
        ai = AIClient(creation_prompt)
        generated_prompt = await ai.get_response()
        
        # Clean up response if needed
        if not generated_prompt or "⚠️" in generated_prompt:
            generated_prompt = "A majestic phoenix made of crystal rising from a nebula, 8k resolution, cinematic lighting"
            
        await message.edit(f"🎨 <b>Visualizing:</b>\n<i>{html.escape(generated_prompt[:100])}...</i>", parse_mode=enums.ParseMode.HTML)
        
        # 2. Generate Image
        image_urls = await IMG_GEN.generate_image(generated_prompt)
        
        if image_urls:
            try:
                await message.delete()
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=image_urls[0],
                    caption=f"🎲 <b>Surprise Creation</b>\n\n<b>Dream:</b> {html.escape(generated_prompt)}\n<b>Model:</b> {Config.DEFAULT_IMG_MODEL}",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send surprise image: {e}")
                await edit_ui(message, "Error", f"Failed to send image: {e}")
        else:
            await edit_ui(message, "Error", "Failed to generate the surprise image.")

    elif cmd == "chaos":
        # Randomize EVERYTHING: Settings + Prompt
        import random as rand
        
        await message.edit("🌪️ <b>CHAOS MODE ACTIVATED</b>\nRandomizing settings...", parse_mode=enums.ParseMode.HTML)
        
        # Randomize Config
        sizes = ["1024x1024","1792x1024", "1024x1792"]
        Config.DEFAULT_IMG_SIZE = rand.choice(sizes)
        Config.DEFAULT_IMG_QUALITY = rand.choice(["standard", "hd"])
        Config.DEFAULT_IMG_STYLE = rand.choice(["vivid", "natural"])
        
        # Pick a random model (Free only to save credits)
        free_models = [k for k, v in Config.AVAILABLE_IMG_MODELS.items() if v.get("tier") == "free"]
        if free_models:
            Config.DEFAULT_IMG_MODEL = rand.choice(free_models)
        else:
            Config.DEFAULT_IMG_MODEL = "phoenix" # Fallback
        
        await message.edit(f"🌪️ <b>CHAOS MODE ACTIVATED</b>\nSettings randomized.\nDreaming up chaos...", parse_mode=enums.ParseMode.HTML)
        
        # Generate multiple chaos prompts for variety
        chaos_prompts = [
            "Generate a bizarre, surreal, and chaotic art prompt that defies logic. Highly detailed. Return ONLY the prompt.",
            "Create an absurd, mind-bending image description with impossible physics and reality. Return ONLY the prompt.",
            "Describe a completely nonsensical scene that breaks all laws of nature. Make it vivid and detailed. Return ONLY the prompt.",
            "Generate a prompt for the most chaotic, random, and unpredictable image imaginable. Return ONLY the prompt.",
            "Create a description of something that cannot exist in reality, full of contradictions. Return ONLY the prompt."
        ]
        
        creation_prompt = rand.choice(chaos_prompts)
        
        try:
            ai = AIClient(creation_prompt)
            generated_prompt = await ai.get_response()
            
            if not generated_prompt or "⚠️" in generated_prompt:
                # Fallback prompts if AI fails
                fallback_prompts = [
                    "Abstract chaos, melting clocks in a cybernetic forest, neon rain",
                    "Surreal nightmare, floating mountains made of jellyfish, lightning storms",
                    "Cosmic horror, impossible geometry, reality breaking apart, psychedelic colors",
                    "Dreamscape chaos, upside-down architecture, liquid time, paradoxical dimensions",
                    "Mad art, mechanical butterflies, crystal oceans, burning ice cream"
                ]
                generated_prompt = rand.choice(fallback_prompts)
        except Exception as e:
            logger.error(f"Chaos prompt generation failed: {e}")
            generated_prompt = "Abstract chaos, melting clocks in a cybernetic forest, neon rain"

        await message.edit(f"🌪️ <b>GENERATING CHAOS...</b>\nPrompt: {html.escape(generated_prompt[:50])}...", parse_mode=enums.ParseMode.HTML)

        try:
            image_urls = await IMG_GEN.generate_image(
                generated_prompt,
                model=Config.DEFAULT_IMG_MODEL,
                size=Config.DEFAULT_IMG_SIZE,
                quality=Config.DEFAULT_IMG_QUALITY,
                style=Config.DEFAULT_IMG_STYLE
            )
            
            if image_urls:
                try:
                    await message.delete()
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=image_urls[0],
                        caption=(
                            f"🌪️ <b>CHAOS GENERATION</b>\n\n"
                            f"<b>Prompt:</b> {html.escape(generated_prompt)}\n"
                            f"<b>Model:</b> {Config.DEFAULT_IMG_MODEL}\n"
                            f"<b>Size:</b> {Config.DEFAULT_IMG_SIZE}\n"
                            f"<b>Quality:</b> {Config.DEFAULT_IMG_QUALITY}\n"
                            f"<b>Style:</b> {Config.DEFAULT_IMG_STYLE}"
                        ),
                        parse_mode=enums.ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Failed to send chaos image: {e}")
                    await edit_ui(message, "❌ Chaos Error", f"Generated image but failed to send: {str(e)[:100]}")
            else:
                await edit_ui(message, "❌ Chaos Failed", "The chaos could not be manifested. Try again!")
                
        except Exception as e:
            logger.error(f"Chaos image generation failed: {e}")
            await edit_ui(message, "❌ Chaos Error", f"Chaos generation failed: {str(e)[:100]}")

    elif cmd == "models":
        await message.edit("📋 <b>Fetching Available Models...</b>", parse_mode=enums.ParseMode.HTML)
        
        # Use local models list instead of API call
        models_list = []
        for model_id, model_info in Config.AVAILABLE_IMG_MODELS.items():
            tier_emoji = "👑" if model_info.get("tier") == "pro" else "🆓"
            async_icon = "⚡" if model_info.get("async") else ""
            description = model_info.get("description", "")
            models_list.append(f"{tier_emoji}{async_icon} <code>{model_id}</code> - {description}")
        
        models_text = "\n".join(models_list)
        await edit_ui(message, "🎨 Available Models", 
                    f"<b>Image Generation Models:</b>\n\n{models_text}\n\n"
                    f"<i>👑 = Pro models | 🆓 = Free models | ⚡ = Async processing</i>\n\n"
                    f"<b>Popular Choices:</b>\n"
                    f"• <code>flux-schnell</code> - Fast & reliable\n"
                    f"• <code>flux2-dev</code> - High quality\n"
                    f"• <code>sdxl</code> - Classic stable diffusion", parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "config":
        # Usage: .img config flux-schnell 1024x1024 2
        if len(args) < 3:
            current_config = (
                f"<b>Current Image Config:</b>\n"
                f"• Model: <code>{Config.DEFAULT_IMG_MODEL}</code>\n"
                f"• Size: <code>{Config.DEFAULT_IMG_SIZE}</code>\n"
                f"• Count: <code>{Config.DEFAULT_IMG_COUNT}</code>\n"
                f"• Quality: <code>{Config.DEFAULT_IMG_QUALITY}</code>\n"
                f"• Style: <code>{Config.DEFAULT_IMG_STYLE}</code>\n\n"
                f"<b>Usage:</b>\n"
                f"<code>.img config [model] [size] [count] [quality] [style]</code>\n\n"
                f"<b>Popular Models:</b>\n"
                f"• flux-schnell (fast)\n"
                f"• flux2-dev (quality)\n"
                f"• sdxl (balanced)\n\n"
                f"<b>Sizes:</b> 1024x1024, 1792x1024, 1024x1792\n"
                f"<b>Qualities:</b> standard, hd\n"
                f"<b>Styles:</b> vivid, natural"
            )
            return await edit_ui(message, "⚙️ Image Config", current_config, parse_mode=enums.ParseMode.HTML)
        
        config_parts = args[2].split()
        if len(config_parts) >= 1:
            # Validate model exists
            if config_parts[0] in Config.AVAILABLE_IMG_MODELS:
                Config.DEFAULT_IMG_MODEL = config_parts[0]
            else:
                return await edit_ui(message, "Error", f"Model '{config_parts[0]}' not found. Use <code>.img models</code> to see available models.", parse_mode=enums.ParseMode.HTML)
        if len(config_parts) >= 2:
            Config.DEFAULT_IMG_SIZE = config_parts[1]
        if len(config_parts) >= 3:
            Config.DEFAULT_IMG_COUNT = min(int(config_parts[2]), 4)
        if len(config_parts) >= 4:
            Config.DEFAULT_IMG_QUALITY = config_parts[3]
        if len(config_parts) >= 5:
            Config.DEFAULT_IMG_STYLE = config_parts[4]
        
        await edit_ui(message, "✅ Config Updated", 
                     f"<b>New Settings:</b>\n"
                     f"• Model: <code>{Config.DEFAULT_IMG_MODEL}</code>\n"
                     f"• Size: <code>{Config.DEFAULT_IMG_SIZE}</code>\n"
                     f"• Count: <code>{Config.DEFAULT_IMG_COUNT}</code>\n"
                     f"• Quality: <code>{Config.DEFAULT_IMG_QUALITY}</code>\n"
                     f"• Style: <code>{Config.DEFAULT_IMG_STYLE}</code>", parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "enhance":
        # Usage: .img enhance A simple cat
        if len(args) < 3:
            return await edit_ui(message, "Usage", "<code>.img enhance [prompt]</code>\n\nThis will enhance your prompt using AI for better image generation results.", parse_mode=enums.ParseMode.HTML)
        
        original_prompt = args[2]
        await message.edit("🧠 <b>Enhancing Prompt...</b>\nAnalyzing with AI...", parse_mode=enums.ParseMode.HTML)
        
        enhanced_prompt = await IMG_GEN.enhance_prompt(original_prompt)
        
        enhancement_info = (
            f"<b>🎨 Prompt Enhancement</b>\n\n"
            f"<b>Original:</b> {original_prompt}\n\n"
            f"<b>Enhanced:</b> {enhanced_prompt}\n\n"
            f"<i>Use <code>.img gen \"{enhanced_prompt}\"</code> to generate with the enhanced prompt!</i>"
        )
        await edit_ui(message, "✨ Prompt Enhanced", enhancement_info, parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "setup":
        await message.edit("🔧 <b>Setting up Image API...</b>", parse_mode=enums.ParseMode.HTML)
        
        success = await IMG_GEN.setup_api_key()
        if success:
            await edit_ui(message, "✅ API Setup Complete", 
                         f"Image generation API is ready!\n\n"
                         f"<b>API Key:</b> <code>{Config.INFIP_API_KEY[:20]}...</code>\n\n"
                         f"Use <code>.img gen [prompt]</code> to generate images.\n"
                         f"Use <code>.img models</code> to see all available models.", parse_mode=enums.ParseMode.HTML)
        else:
            await edit_ui(message, "❌ Setup Failed", 
                         "Failed to set up image generation API. Please check your internet connection.", parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "random":
        # Randomize image generation parameters
        import random as rand
        
        # Random size selection
        sizes = ["1024x1024","1792x1024", "1024x1792"]
        random_size = rand.choice(sizes)
        
        # Random count (1-4)
        random_count = 1
        
        # Random quality
        qualities = ["standard", "hd"]
        random_quality = rand.choice(qualities)
        
        # Random style
        styles = ["vivid", "natural"]
        random_style = rand.choice(styles)
        
        # Random model (Free models only)
        free_models = [k for k, v in Config.AVAILABLE_IMG_MODELS.items() if v.get("tier") == "free"]
        
        if free_models:
            random_model = rand.choice(free_models)
        else:
            random_model = Config.DEFAULT_IMG_MODEL
        
        # Apply random settings
        Config.DEFAULT_IMG_SIZE = random_size
        Config.DEFAULT_IMG_COUNT = random_count
        Config.DEFAULT_IMG_QUALITY = random_quality
        Config.DEFAULT_IMG_STYLE = random_style
        Config.DEFAULT_IMG_MODEL = random_model
        
        random_info = (
            f"<b>🎲 Randomized Settings Applied!</b>\n\n"
            f"• <b>Model:</b> <code>{random_model}</code>\n"
            f"• <b>Size:</b> <code>{random_size}</code>\n"
            f"• <b>Count:</b> <code>{random_count}</code>\n"
            f"• <b>Quality:</b> <code>{random_quality}</code>\n"
            f"• <b>Style:</b> <code>{random_style}</code>\n\n"
            f"<i>🎯 Ready to generate with random parameters!</i>\n"
            f"Use <code>.img gen [prompt]</code> to create images with these settings."
        )
        await edit_ui(message, "🎲 Random Settings", random_info, parse_mode=enums.ParseMode.HTML)
    
    elif cmd == "cache":
        # Clear image generation cache
        IMG_GEN.clear_cache()
        await edit_ui(message, "🗑️ Cache Cleared", "Image generation cache has been cleared.", parse_mode=enums.ParseMode.HTML)
    
    else:
        help_text = (
            "<b>🎨 Enhanced Image Generation Commands:</b>\n\n"
            "• <code>.img gen [prompt]</code> - Generate image\n"
            "• <code>.img surprise [topic]</code> - AI-Dreamed random image\n"
            "• <code>.img chaos</code> - Random settings + Random prompt\n"
            "• <code>.img models</code> - Show all available models\n"
            "• <code>.img config [model] [size] [count] [quality] [style]</code> - Configure settings\n"
            "• <code>.img random</code> - Randomize settings only\n"
            "• <code>.img enhance [prompt]</code> - AI-enhance your prompt\n"
            "• <code>.img setup</code> - Setup API key\n"
            "• <code>.img cache</code> - Clear generation cache\n\n"
            "<b>Examples:</b>\n"
            f"• <code>.img gen A beautiful sunset</code>\n"
            f"• <code>.img surprise Cyberpunk</code>\n"
            f"• <code>.img chaos</code>\n\n"
            f"<b>Current Model:</b> <code>{Config.DEFAULT_IMG_MODEL}</code>\n"
            f"<b>Available Models:</b> {len(Config.AVAILABLE_IMG_MODELS)} models"
        )
        await edit_ui(message, "🎨 Image Generation", help_text, parse_mode=enums.ParseMode.HTML)

# =================================================================================================
# ✍️ AUTO-ENHANCE COMMAND
# =================================================================================================

@Client.on_message(filters.command("auto-enhance", prefix) & filters.me)
async def auto_enhance_handler(client: Client, message: Message):
    """Toggle auto-enhancement feature for owner's messages."""
    args = message.text.split(" ", 1)
    action = args[1].lower() if len(args) > 1 else "status"
    
    # Initialize the setting if not exists
    if not hasattr(GEMS, 'auto_enhance_enabled'):
        GEMS.auto_enhance_enabled = True
    
    if action == "on":
        GEMS.auto_enhance_enabled = True
        await edit_ui(message, "✍️ Auto-Enhance", "Message auto-enhancement has been <b>ENABLED</b>.\n\nYour messages will now be automatically edited to fix mistakes and improve clarity.")
        
    elif action == "off":
        GEMS.auto_enhance_enabled = False
        await edit_ui(message, "✍️ Auto-Enhance", "Message auto-enhancement has been <b>DISABLED</b>.\n\nYour messages will be sent as-is without automatic corrections.")
        
    elif action == "status":
        status = "✅ ENABLED" if GEMS.auto_enhance_enabled else "❌ DISABLED"
        info_text = (
            f"<b>Auto-Enhance Status:</b> {status}\n\n"
            f"<b>What it does:</b>\n"
            f"• Fixes spelling & grammar mistakes\n"
            f"• Improves text clarity\n"
            f"• Preserves your original tone\n"
            f"• Works automatically in all chats\n\n"
            f"<b>Usage:</b>\n"
            f"• <code>.auto-enhance on</code> - Enable feature\n"
            f"• <code>.auto-enhance off</code> - Disable feature\n"
            f"• <code>.auto-enhance status</code> - Show status"
        )
        await edit_ui(message, "✍️ Auto-Enhance", info_text)
        
    else:
        await edit_ui(message, "Usage", "Invalid option. Use: <code>.auto-enhance [on|off|status]</code>")

# =================================================================================================
# ✍️ OWNER MESSAGE ENHANCER
# =================================================================================================

@Client.on_message(filters.me & ~filters.command([f"api", f"gem", f"gai", f"auto-enhance", f"img"], prefix) & ~filters.service, group=49)
async def owner_message_enhancer(client: Client, message: Message):
    """Enhances owner's messages by fixing mistakes and improving text quality."""
    try:
        # Check if auto-enhance is enabled
        if not hasattr(GEMS, 'auto_enhance_enabled') or not GEMS.auto_enhance_enabled:
            return
            
        # Skip if message is empty or just media
        if not (message.text or message.caption):
            return
            
        original_text = message.text or message.caption or ""
        
        # Skip very short messages (less than 5 characters)
        if len(original_text.strip()) < 5:
            return
            
        # Skip if it looks like a command
        if original_text.strip().startswith(prefix):
            return
            
        # Small delay to make it feel natural
        await asyncio.sleep(random.uniform(0.3, 1.0))
        
        # Create enhancement prompt
        enhancement_prompt = (
            f"Enhance this message by fixing any spelling/grammar mistakes and improving clarity while keeping the original meaning intact.also use complex english if it is in english and for different language dont change language also do not chnage meaning of text"
            f"Keep the same tone and style. Return ONLY the enhanced text, no explanations.\n\n"
            f"Original: {original_text}"
        )
        
        # Get enhanced version
        ai = AIClient(enhancement_prompt)
        enhanced_text = await ai.get_response()
        
        # Skip if AI returned an error or empty response
        if not enhanced_text or enhanced_text.startswith("⚠️") or not enhanced_text.strip():
            return
            
        # Only edit if the enhanced version is actually different and better
        if enhanced_text.strip() != original_text.strip() and len(enhanced_text.strip()) > 0:
            try:
                # Default to MARKDOWN to avoid HTML entity errors
                await message.edit(enhanced_text.strip(), parse_mode=enums.ParseMode.MARKDOWN)
                logger.info(f"Message enhanced: '{original_text[:30]}...' -> '{enhanced_text[:30]}...'")
            except Exception:
                try:
                    # Fallback to plain text if Markdown fails
                    await message.edit(enhanced_text.strip(), parse_mode=enums.ParseMode.DISABLED)
                except Exception as e:
                    logger.debug(f"Failed to edit enhanced message: {e}")
                
    except Exception as e:
        logger.error(f"Error in owner_message_enhancer: {e}")

# =================================================================================================
# 👁️ EVENT WATCHER (THE BRAIN)
# =================================================================================================

# Added group=50 to ensure the AI watcher isn't blocked by other modules
@Client.on_message(filters.incoming & ~filters.me & ~filters.service, group=50)
async def ai_watcher(client: Client, message: Message):
    try:
        # Determine Context
        user_id = message.from_user.id if message.from_user else 0
        chat_id = message.chat.id
        
        data = None
        source_type = None 

        # Priority 1: Global Stalker
        if user_id in GEMS.global_stalk_targets:
            data = GEMS.global_stalk_targets[user_id]
            source_type = 'global'

        # Priority 2: Local Target
        elif user_id in GEMS.active_targets:
            data = GEMS.active_targets[user_id]
            source_type = 'local_target'

        # Priority 3: Active Chat
        elif chat_id in GEMS.active_chats:
            if message.from_user and message.from_user.is_bot: return 
            data = GEMS.active_chats[chat_id]
            source_type = 'chat'

        # Priority 4: DM Mode
        elif message.chat.type == enums.ChatType.PRIVATE and GEMS.dm_mode_active:
             gem_content = GEMS.active_dm_gem or GEMS.default_persona
             data = {"gem": gem_content, "history": []} 
             source_type = 'dm'

        if data:
            await process_advanced_reply(client, message, data, source_type)

    except Exception as e:
        logger.error(f"Watcher Error: {e}")

async def process_advanced_reply(client: Client, message: Message, data: Dict, source: str):
    """Handles Image processing, Human Mimicry, and AI Generation."""
    
    if not message or not data:
        logger.error("Invalid parameters in process_advanced_reply")
        return
        
    try:
        # 1. Input Analysis
        input_text = message.text or message.caption or ""
        image_url_list = []
        
        # Handle Image Input
        if message.photo:
            input_text = f"[Photo Sent] {input_text}"
            downloaded_path = None
            try:
                downloaded_path = await client.download_media(message.photo)
                if downloaded_path:
                    uploader = ImageUploader()
                    url = await uploader.upload(downloaded_path)
                    if url: 
                        image_url_list.append(url)
            except Exception as e:
                logger.error(f"Image processing error: {e}")
            finally:
                # Clean up downloaded file
                if downloaded_path and os.path.exists(downloaded_path):
                    try:
                        os.remove(downloaded_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file: {e}")

        # 2. Add to History
        GEMS.add_history(data, "User", input_text)
        
        # 3. Build Prompt
        full_prompt = GEMS.build_prompt(data['gem'], data['history'], input_text)
        
        # 4. HUMAN MIMICRY (PHASE 1: READING)
        await HumanBehavior.simulate_reading(client, message.chat.id, input_text, is_image=(len(image_url_list) > 0))

        # 5. AI Generation
        # Check circuit breaker before making API call
        if RECOVERY_MANAGER.is_circuit_open():
            try:
                fallback = await RECOVERY_MANAGER.handle_error("CIRCUIT_BREAKER")
                await HumanBehavior.simulate_typing(client, message.chat.id, fallback)
                await message.reply(fallback, parse_mode=enums.ParseMode.HTML)
                return
            except Exception:
                return
        
        ai = AIClient(full_prompt, image_urls=image_url_list)
        response = await ai.get_response()
        
        # Check if response indicates an error
        if response.startswith("⚠️"):
            fallback = await RECOVERY_MANAGER.handle_error("AI_API_ERROR")
            if fallback:
                response = fallback
        else:
            await RECOVERY_MANAGER.handle_success()
        
        if not response or not response.strip():
            logger.warning("Empty AI response received")
            return
        
        # 6. HUMAN MIMICRY (PHASE 2: TYPING)
        await HumanBehavior.simulate_typing(client, message.chat.id, response)
        
        # 7. Final Send - ROBUST FALLBACK SYSTEM
        GEMS.add_history(data, "AI", response)
        try:
            # Try Markdown first (Best for code blocks, bold, etc.)
            await message.reply(response, parse_mode=enums.ParseMode.MARKDOWN)
        except Exception:
            try:
                # Fallback to HTML, escaping content to prevent tag errors
                # This handles cases like "x < y" or unclosed asterisks
                await message.reply(html.escape(response), parse_mode=enums.ParseMode.HTML)
            except Exception:
                # Final fallback: Raw text. Guarantees message delivery.
                await message.reply(response, parse_mode=enums.ParseMode.DISABLED)
                
    except Exception as e:
        logger.error(f"Error in process_advanced_reply: {e}")

# =================================================================================================
# 🎭 DYNAMIC PROFILE SYSTEM
# =================================================================================================

class DynamicProfile:
    """Manages dynamic profile updates with AI-generated content."""
    
    def __init__(self):
        self.db_name = "dynamic_profile.db"
        self.update_interval = 3600  # 1 hour in seconds
        self.max_pfp_history = 50
        self._scheduler_task = None
        self._db_lock = asyncio.Lock()
        
    async def ensure_db(self):
        """Ensure profile database tables exist."""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS profile_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS pfp_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        prompt TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS profile_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                await db.commit()
        except Exception as e:
            logger.error(f"Profile database initialization error: {e}")
            raise
    
    async def save_profile_data(self, data_type: str, content: str):
        """Save profile data to history."""
        async with self._db_lock:
            try:
                await self.ensure_db()
                async with aiosqlite.connect(self.db_name) as db:
                    await db.execute(
                        "INSERT INTO profile_history (type, content) VALUES (?, ?)",
                        (data_type, content)
                    )
                    await db.commit()
                    logger.info(f"Saved {data_type} to profile history")
            except Exception as e:
                logger.error(f"Failed to save profile data: {e}")
    
    async def get_profile_history(self, data_type: str, limit: int = 10) -> List[str]:
        """Get profile history by type."""
        try:
            await self.ensure_db()
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    "SELECT content FROM profile_history WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
                    (data_type, limit)
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get profile history: {e}")
            return []
    
    async def save_pfp(self, file_path: str, prompt: str):
        """Save profile picture to history."""
        async with self._db_lock:
            try:
                await self.ensure_db()
                async with aiosqlite.connect(self.db_name) as db:
                    # Check if we need to clean old entries
                    cursor = await db.execute("SELECT COUNT(*) FROM pfp_history")
                    count = (await cursor.fetchone())[0]
                    
                    if count >= self.max_pfp_history:
                        # Delete oldest entries
                        await db.execute(
                            "DELETE FROM pfp_history WHERE id IN (SELECT id FROM pfp_history ORDER BY timestamp ASC LIMIT ?)",
                            (count - self.max_pfp_history + 1,)
                        )
                    
                    await db.execute(
                        "INSERT INTO pfp_history (file_path, prompt) VALUES (?, ?)",
                        (file_path, prompt)
                    )
                    await db.commit()
                    logger.info(f"Saved PFP to history: {file_path}")
            except Exception as e:
                logger.error(f"Failed to save PFP: {e}")
    
    async def get_pfp_history(self, limit: int = 10) -> List[Dict]:
        """Get profile picture history."""
        try:
            await self.ensure_db()
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    "SELECT file_path, prompt, timestamp FROM pfp_history ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                rows = await cursor.fetchall()
                return [
                    {
                        "file_path": row[0],
                        "prompt": row[1],
                        "timestamp": row[2]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get PFP history: {e}")
            return []
    
    async def generate_name(self) -> str:
        """Generate AI-powered creative name with different fonts and styles."""
        try:
            font_styles = [
                "Use Unicode symbols and special characters",
                "Use aesthetic letters and fancy fonts", 
                "Use cool modern slang and abbreviations",
                "Use emoji and special characters creatively",
                "Use cyberpunk/futuristic style",
                "Use minimalist aesthetic style",
                "Use bold and dramatic styling"
            ]
            
            chosen_style = random.choice(font_styles)
            
            prompt = (
                f"Generate a unique, creative, and memorable username or display name. "
                f"{chosen_style}. Make it stand out and look different from regular names. "
                f"Use Unicode characters, symbols, or creative formatting if appropriate. "
                f"Return ONLY the name, no explanations. Make it 1-20 characters max."
            )
            ai = AIClient(prompt)
            name = await ai.get_response()
            
            if name and not name.startswith("⚠️"):
                clean_name = name.strip()
                # Remove markdown formatting but keep Unicode/special characters
                clean_name = clean_name.replace("**", "").replace("__", "").replace("~~", "")
                await self.save_profile_data("name", clean_name)
                logger.info(f"Generated name with style '{chosen_style}': {clean_name}")
                return clean_name
            return None
        except Exception as e:
            logger.error(f"Failed to generate name: {e}")
            return None
    
    async def generate_bio(self) -> str:
        """Generate AI-powered creative bio with better formatting."""
        try:
            bio_styles = [
                "mysterious and intriguing",
                "funny and witty",
                "philosophical and deep",
                "minimalist and clean",
                "energetic and enthusiastic",
                "dark and edgy",
                "professional and impressive",
                "chaotic and random",
                "aesthetic and poetic",
                "tech-focused and nerdy"
            ]
            
            chosen_style = random.choice(bio_styles)
            
            prompt = (
                f"Generate a creative, interesting, and unique bio for a social media profile. "
                f"Make it {chosen_style}. Keep it under 70 characters (Telegram limit). "
                f"Use creative language, maybe include an emoji or special character. "
                f"Make it memorable and attention-grabbing. "
                f"Return ONLY the bio text, no explanations or quotes."
            )
            ai = AIClient(prompt)
            bio = await ai.get_response()
            
            if bio and not bio.startswith("⚠️"):
                clean_bio = bio.strip()
                # Remove quotes but keep emojis and special characters
                clean_bio = clean_bio.replace('"', '').replace("'", "")
                # Ensure it's within Telegram's bio limit
                if len(clean_bio) <= 70:
                    await self.save_profile_data("bio", clean_bio)
                    logger.info(f"Generated bio with style '{chosen_style}': {clean_bio}")
                    return clean_bio
                else:
                    # Try again with shorter version
                    return await self.generate_bio()
            return None
        except Exception as e:
            logger.error(f"Failed to generate bio: {e}")
            return None
    
    async def generate_pfp(self) -> Optional[str]:
        """Generate AI-powered profile picture with beautiful aesthetic art using AI for enhanced range and depth."""
        try:
            # AI-powered prompt generation for maximum variety and depth
            ai_prompt_categories = {
                "anime_landscapes": "Generate a detailed, emotional anime landscape prompt inspired by Makoto Shinkai or Studio Ghibli. Include specific time of day, weather, lighting, emotional mood, and detailed background elements. Make it cinematic and nostalgic. Return ONLY the prompt.",
                "nature_aesthetics": "Generate a beautiful nature photography prompt with specific lighting conditions (golden hour, misty morning, etc.), location details, atmospheric elements, and artistic composition. Include emotional qualities and visual details. Return ONLY the prompt.",
                "animal_art": "Generate a wildlife art prompt featuring a specific animal in its natural habitat. Include detailed description of the animal's appearance, behavior, environment, lighting, and emotional atmosphere. Make it artistic and professional. Return ONLY the prompt.",
                "fantasy_worlds": "Generate an epic fantasy landscape prompt with magical elements, mythical creatures, and otherworldly features. Include detailed descriptions of architecture, lighting, colors, and mystical atmosphere. Return ONLY the prompt.",
                "cyberpunk_cityscapes": "Generate a cyberpunk cityscape prompt with futuristic elements, neon lighting, advanced technology, and urban atmosphere. Include specific time of day, weather, architectural details, and mood. Return ONLY the prompt.",
                "ethereal_scenes": "Generate an ethereal, dreamlike scene prompt with soft colors, floating elements, magical atmosphere, and surreal beauty. Include specific lighting, textures, and emotional qualities. Return ONLY the prompt.",
                "seasonal_beauty": "Generate a seasonal landscape prompt capturing the essence of a specific season. Include detailed weather conditions, natural elements, colors, lighting, and seasonal atmosphere. Make it emotionally resonant. Return ONLY the prompt.",
                "cosmic_scenes": "Generate a cosmic or space scene prompt with celestial elements, nebulae, stars, planets, or astronomical phenomena. Include specific colors, lighting effects, scale, and cosmic atmosphere. Return ONLY the prompt.",
                "water_scenes": "Generate a water-focused scene prompt (ocean, lake, river, waterfall) with detailed water movement, reflections, lighting, and surrounding environment. Include peaceful or dramatic atmosphere. Return ONLY the prompt.",
                "mountain_landscapes": "Generate a majestic mountain landscape prompt with specific peak formations, weather conditions, lighting, elevation details, and surrounding nature. Include sense of scale and atmosphere. Return ONLY the prompt.",
                "vintage_aesthetics": "Generate a vintage-style scene prompt with specific era (1920s-80s), color palette, texture, and nostalgic elements. Include authentic period details and atmosphere. Return ONLY the prompt.",
                "minimalist_art": "Generate a minimalist art prompt with simple geometric shapes, limited color palette, clean composition, and abstract representation of natural elements. Include sense of calm and modern aesthetic. Return ONLY the prompt.",
                "ghibli_nature": "Generate a Studio Ghibli-inspired nature prompt with hand-drawn animation style, nostalgic atmosphere, gentle lighting, and heartwarming elements. Include specific Ghibli-esque details and mood. Return ONLY the prompt.",
                "abstract_nature": "Generate an abstract interpretation of nature using shapes, colors, and patterns to represent natural elements. Include emotional qualities and artistic style. Return ONLY the prompt."
            }
            
            # Randomly select a category
            category = random.choice(list(ai_prompt_categories.keys()))
            ai_prompt = ai_prompt_categories[category]
            
            logger.info(f"Generating AI prompt for category '{category}'")
            
            # Use AI to generate a unique, detailed prompt
            try:
                ai = AIClient(ai_prompt)
                generated_prompt = await ai.get_response()
                
                if not generated_prompt or generated_prompt.startswith("⚠️"):
                    # Fallback to predefined prompts if AI fails
                    generated_prompt = self.get_fallback_prompt(category)
                
                # Clean up the AI response
                generated_prompt = generated_prompt.strip()
                if generated_prompt.startswith('"') and generated_prompt.endswith('"'):
                    generated_prompt = generated_prompt[1:-1]
                
            except Exception as e:
                logger.error(f"AI prompt generation failed: {e}")
                generated_prompt = self.get_fallback_prompt(category)
            
            # Add quality and style modifiers
            quality_modifiers = [
                "highly detailed, 8k resolution, professional photography",
                "ultra realistic, sharp focus, dramatic lighting",
                "masterpiece, best quality, intricate details",
                "cinematic quality, professional color grading",
                "award winning photography, perfect composition",
                "breathtakingly beautiful, stunning visual quality",
                "professional art print quality, gallery worthy"
            ]
            
            style_modifiers = [
                "emotional and atmospheric",
                "serene and peaceful mood",
                "breathtaking and awe-inspiring",
                "nostalgic and heartwarming",
                "magical and enchanting",
                "dramatic and powerful",
                "dreamy and ethereal"
            ]
            
            final_prompt = f"{generated_prompt}, {random.choice(quality_modifiers)}, {random.choice(style_modifiers)}"
            logger.info(f"Final PFP prompt: {final_prompt}")
            
            # Try multiple models for better quality
            models_to_try = ["flux2-dev", "flux-schnell", "sdxl", "phoenix"]
            
            for model in models_to_try:
                try:
                    image_urls = await IMG_GEN.generate_image(
                        final_prompt, 
                        model=model, 
                        size="1024x1024", 
                        count=1,
                        quality="hd",
                        style="vivid"
                    )
                    
                    if image_urls:
                        # Download the image
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.get(image_urls[0])
                            if response.status_code == 200:
                                # Save to local file
                                timestamp = int(time.time())
                                filename = f"dynamic_pfp_{category}_{timestamp}.jpg"
                                filepath = os.path.join("downloads", filename)
                                
                                # Ensure downloads directory exists
                                os.makedirs("downloads", exist_ok=True)
                                
                                with open(filepath, "wb") as f:
                                    f.write(response.content)
                                
                                await self.save_pfp(filepath, final_prompt)
                                logger.info(f"Generated and saved PFP: {filepath}")
                                return filepath
                except Exception as e:
                    logger.warning(f"Failed with model {model}: {e}")
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Failed to generate PFP: {e}")
            return None
    
    def get_fallback_prompt(self, category: str) -> str:
        """Get fallback prompt if AI generation fails."""
        fallback_prompts = {
            "anime_landscapes": "A peaceful anime night landscape inspired by Your Name, children near a reflective lake, fireflies, glowing stars and Milky Way, gentle moonlight, serene atmosphere, soft pastel colors, cinematic composition, detailed anime background art, emotional and nostalgic mood",
            "nature_aesthetics": "Aesthetic nature photography, misty morning forest with sunbeams filtering through trees, dew drops on spider webs, foggy atmosphere, golden hour lighting, peaceful and serene, ultra high quality, professional nature photography",
            "animal_art": "Beautiful aesthetic fox in autumn forest, golden leaves falling, soft lighting, peaceful wildlife photography, detailed fur, intelligent eyes, warm orange and red colors, serene nature moment",
            "fantasy_worlds": "Fantasy landscape with floating islands, waterfalls falling into sky, magical bridges connecting islands, dragons flying in distance, ethereal lighting, vibrant colors, detailed fantasy art",
            "cyberpunk_cityscapes": "Cyberpunk cityscape at night, neon lights reflecting on wet streets, flying cars, towering skyscrapers with holographic ads, futuristic architecture, vibrant purple and blue colors, dystopian beauty",
            "ethereal_scenes": "Ethereal dream landscape, soft pastel colors, floating elements, magical atmosphere, surreal beauty, peaceful and otherworldly, fantasy art style, dreamlike quality",
            "seasonal_beauty": "Beautiful spring landscape, cherry blossoms, pink petals falling, gentle breeze, peaceful garden, soft pastel colors, fresh spring atmosphere, detailed nature photography",
            "cosmic_scenes": "Beautiful cosmic landscape, nebula clouds, stars, planets, ethereal space scene, vibrant purple and blue colors, peaceful space atmosphere, detailed space art",
            "water_scenes": "Peaceful lake landscape, calm water reflecting mountains, serene atmosphere, detailed water reflection, peaceful nature scene, beautiful landscape photography",
            "mountain_landscapes": "Majestic mountain range at sunrise, golden light, dramatic peaks, peaceful mountain landscape, detailed nature photography, breathtaking mountain beauty",
            "vintage_aesthetics": "Vintage 80s aesthetic landscape, neon sunset, retro color palette, synthwave style, mountains silhouetted, grid lines, nostalgic 80s feel, retro futurism",
            "minimalist_art": "Minimalist landscape art, simple geometric shapes representing mountains and sun, limited color palette, clean lines, modern aesthetic, abstract nature representation",
            "ghibli_nature": "Studio Ghibli style landscape, rolling green hills, fluffy clouds, peaceful countryside, small cottage with garden, warm sunlight, nostalgic atmosphere, hand-drawn animation style",
            "abstract_nature": "Abstract nature interpretation with flowing shapes and colors representing wind and water, artistic style, emotional qualities, modern aesthetic"
        }
        return fallback_prompts.get(category, "Beautiful aesthetic landscape, peaceful atmosphere, high quality art")
    
    async def update_telegram_profile(self, client: Client, name: str = None, bio: str = None, pfp_path: str = None):
        """Update Telegram profile with new data."""
        try:
            updates_made = []
            
            # Update name if provided
            if name:
                try:
                    # Get current profile info
                    me = await client.get_me()
                    current_name = me.first_name if me else ""
                    
                    # Only update if name is different
                    if name != current_name:
                        await client.update_profile(first_name=name)
                        updates_made.append(f"Name: {name}")
                        logger.info(f"Updated profile name: {name}")
                    else:
                        logger.info("Name unchanged, skipping update")
                except Exception as e:
                    logger.error(f"Failed to update name: {e}")
            
            # Update bio if provided
            if bio:
                try:
                    # Get current bio
                    me = await client.get_me()
                    current_bio = me.bio if me and hasattr(me, 'bio') else ""
                    
                    # Only update if bio is different
                    if bio != current_bio:
                        await client.update_profile(bio=bio)
                        updates_made.append(f"Bio: {bio}")
                        logger.info(f"Updated profile bio: {bio}")
                    else:
                        logger.info("Bio unchanged, skipping update")
                except Exception as e:
                    logger.error(f"Failed to update bio: {e}")
                    # Try alternative method
                    try:
                        await client.set_bio(bio)
                        updates_made.append(f"Bio: {bio}")
                        logger.info(f"Updated bio using alternative method: {bio}")
                    except Exception as e2:
                        logger.error(f"Alternative bio update also failed: {e2}")
            
            # Update profile picture if provided
            if pfp_path and os.path.exists(pfp_path):
                try:
                    # Delete current profile photos first to avoid accumulation
                    try:
                        photos = await client.get_profile_photos("me")
                        if photos:
                            await client.delete_profile_photos(photos[0].file_id)
                            logger.info("Deleted previous profile photo")
                    except Exception as e:
                        logger.warning(f"Could not delete previous profile photo: {e}")
                    
                    # Set new profile photo
                    await client.set_profile_photo(photo=pfp_path)
                    updates_made.append(f"PFP: {os.path.basename(pfp_path)}")
                    logger.info(f"Updated profile picture: {pfp_path}")
                except Exception as e:
                    logger.error(f"Failed to update PFP: {e}")
            
            return updates_made
            
        except Exception as e:
            logger.error(f"Failed to update Telegram profile: {e}")
            return []
    
    async def perform_full_update(self, client: Client):
        """Perform a complete profile update."""
        try:
            logger.info("Starting dynamic profile update...")
            
            # Generate new content
            name_task = self.generate_name()
            bio_task = self.generate_bio()
            pfp_task = self.generate_pfp()
            
            # Wait for all tasks to complete
            name, bio, pfp_path = await asyncio.gather(
                name_task, bio_task, pfp_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(name, Exception):
                logger.error(f"Name generation failed: {name}")
                name = None
            if isinstance(bio, Exception):
                logger.error(f"Bio generation failed: {bio}")
                bio = None
            if isinstance(pfp_path, Exception):
                logger.error(f"PFP generation failed: {pfp_path}")
                pfp_path = None
            
            # Update profile with whatever we got
            updates = await self.update_telegram_profile(client, name, bio, pfp_path)
            
            if updates:
                logger.info(f"Profile updated successfully: {', '.join(updates)}")
                return updates
            else:
                logger.warning("No profile updates were made")
                return []
                
        except Exception as e:
            logger.error(f"Full profile update failed: {e}")
            return []
    
    async def start_scheduler(self, client: Client):
        """Start the automatic profile update scheduler."""
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(self._scheduler_loop(client))
            logger.info("Dynamic profile scheduler started")
    
    async def stop_scheduler(self):
        """Stop the automatic profile update scheduler."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("Dynamic profile scheduler stopped")
    
    async def _scheduler_loop(self, client: Client):
        """Main scheduler loop for automatic updates."""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                await self.perform_full_update(client)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Initialize the dynamic profile system
DYNAMIC_PROFILE = DynamicProfile()

# =================================================================================================
# 🎭 DYNAMIC PROFILE COMMANDS
# =================================================================================================

@Client.on_message(filters.command("profile", prefix) & filters.me)
async def profile_handler(client: Client, message: Message):
    """Handle dynamic profile management commands."""
    args = message.text.split(" ", 2)
    cmd = args[1].lower() if len(args) > 1 else "help"
    
    if cmd == "update":
        # Manual profile update
        await message.edit("🎭 <b>Updating Profile...</b>\nGenerating new content...", parse_mode=enums.ParseMode.HTML)
        
        updates = await DYNAMIC_PROFILE.perform_full_update(client)
        
        if updates:
            await edit_ui(message, "✅ Profile Updated", 
                        f"<b>Successfully updated:</b>\n" + "\n".join(f"• {update}" for update in updates))
        else:
            await edit_ui(message, "❌ Update Failed", "No profile updates were made. Please check logs.")
    
    elif cmd == "auto":
        # Toggle automatic updates
        action = args[2].lower() if len(args) > 2 else "status"
        
        if action == "on":
            await DYNAMIC_PROFILE.start_scheduler(client)
            await edit_ui(message, "🤖 Auto Profile", 
                        "Automatic profile updates have been <b>ENABLED</b>.\n\n"
                        f"Your profile will update every {DYNAMIC_PROFILE.update_interval // 3600} hour(s).")
        
        elif action == "off":
            await DYNAMIC_PROFILE.stop_scheduler()
            await edit_ui(message, "🤖 Auto Profile", 
                        "Automatic profile updates have been <b>DISABLED</b>.")
        
        elif action == "status":
            is_running = DYNAMIC_PROFILE._scheduler_task and not DYNAMIC_PROFILE._scheduler_task.done()
            status = "✅ RUNNING" if is_running else "❌ STOPPED"
            await edit_ui(message, "🤖 Auto Profile Status", 
                        f"<b>Status:</b> {status}\n\n"
                        f"<b>Update Interval:</b> {DYNAMIC_PROFILE.update_interval // 3600} hour(s)\n"
                        f"<b>Max PFP History:</b> {DYNAMIC_PROFILE.max_pfp_history} images")
        
        else:
            await edit_ui(message, "Usage", 
                        "Invalid option. Use: <code>.profile auto [on|off|status]</code>")
    
    elif cmd == "name":
        # Generate new name only
        await message.edit("🎭 <b>Generating New Name...</b>", parse_mode=enums.ParseMode.HTML)
        
        name = await DYNAMIC_PROFILE.generate_name()
        if name:
            updates = await DYNAMIC_PROFILE.update_telegram_profile(client, name=name)
            if updates:
                await edit_ui(message, "✅ Name Updated", f"New name: <b>{html.escape(name)}</b>")
            else:
                await edit_ui(message, "❌ Failed", "Failed to update name.")
        else:
            await edit_ui(message, "❌ Failed", "Failed to generate name.")
    
    elif cmd == "bio":
        # Generate new bio only
        await message.edit("🎭 <b>Generating New Bio...</b>", parse_mode=enums.ParseMode.HTML)
        
        bio = await DYNAMIC_PROFILE.generate_bio()
        if bio:
            updates = await DYNAMIC_PROFILE.update_telegram_profile(client, bio=bio)
            if updates:
                await edit_ui(message, "✅ Bio Updated", f"New bio: <i>{html.escape(bio)}</i>")
            else:
                await edit_ui(message, "❌ Failed", "Failed to update bio.")
        else:
            await edit_ui(message, "❌ Failed", "Failed to generate bio.")
    
    elif cmd == "pfp":
        # Generate new profile picture only
        await message.edit("🎭 <b>Generating New Profile Picture...</b>", parse_mode=enums.ParseMode.HTML)
        
        pfp_path = await DYNAMIC_PROFILE.generate_pfp()
        if pfp_path:
            updates = await DYNAMIC_PROFILE.update_telegram_profile(client, pfp_path=pfp_path)
            if updates:
                await edit_ui(message, "✅ PFP Updated", "New profile picture has been set!")
            else:
                await edit_ui(message, "❌ Failed", "Failed to update profile picture.")
        else:
            await edit_ui(message, "❌ Failed", "Failed to generate profile picture.")
    
    elif cmd == "history":
        # Show profile history
        history_type = args[2].lower() if len(args) > 2 else "all"
        
        if history_type == "names":
            history = await DYNAMIC_PROFILE.get_profile_history("name", limit=10)
            if history:
                history_text = "\n".join([f"• {html.escape(name)}" for name in history])
                await edit_ui(message, "📝 Name History", history_text)
            else:
                await edit_ui(message, "📝 Name History", "No name history found.")
        
        elif history_type == "bios":
            history = await DYNAMIC_PROFILE.get_profile_history("bio", limit=10)
            if history:
                history_text = "\n".join([f"• <i>{html.escape(bio)}</i>" for bio in history])
                await edit_ui(message, "📝 Bio History", history_text)
            else:
                await edit_ui(message, "📝 Bio History", "No bio history found.")
        
        elif history_type == "pfps":
            history = await DYNAMIC_PROFILE.get_pfp_history(limit=10)
            if history:
                history_text = "\n".join([
                    f"• {os.path.basename(item['file_path'])}\n  <i>Prompt: {html.escape(item['prompt'][:50])}...</i>"
                    for item in history
                ])
                await edit_ui(message, "🖼️ PFP History", history_text)
            else:
                await edit_ui(message, "🖼️ PFP History", "No PFP history found.")
        
        else:
            await edit_ui(message, "Usage", 
                        "Invalid option. Use: <code>.profile history [names|bios|pfps]</code>")
    
    elif cmd == "interval":
        # Set update interval
        if len(args) < 3:
            current_hours = DYNAMIC_PROFILE.update_interval // 3600
            return await edit_ui(message, "⏰ Update Interval", 
                                f"Current interval: <b>{current_hours}</b> hour(s)\n\n"
                                f"Usage: <code>.profile interval [hours]</code>\n"
                                f"Example: <code>.profile interval 2</code>")
        
        try:
            hours = float(args[2])
            if hours < 0.5:  # Minimum 30 minutes
                return await edit_ui(message, "Error", "Minimum interval is 0.5 hours (30 minutes).")
            
            DYNAMIC_PROFILE.update_interval = int(hours * 3600)
            await edit_ui(message, "⏰ Interval Updated", 
                        f"Update interval set to <b>{hours}</b> hour(s).\n\n"
                        f"Auto-updater will use this new interval.")
        except ValueError:
            await edit_ui(message, "Error", "Invalid number. Use: <code>.profile interval [hours]</code>")
    
    else:
        help_text = (
            "<b>🎭 Dynamic Profile Commands:</b>\n\n"
            "• <code>.profile update</code> - Update all profile elements now\n"
            "• <code>.profile name</code> - Generate new name only\n"
            "• <code>.profile bio</code> - Generate new bio only\n"
            "• <code>.profile pfp</code> - Generate new profile picture only\n"
            "• <code>.profile auto [on|off|status]</code> - Control automatic updates\n"
            "• <code>.profile interval [hours]</code> - Set update interval\n"
            "• <code>.profile history [names|bios|pfps]</code> - View history\n\n"
            "<b>Features:</b>\n"
            "• AI-generated creative names and bios\n"
            "• AI-generated unique profile pictures\n"
            "• Automatic hourly updates\n"
            "• Keeps history of all changes\n"
            "• Previous profile pictures are saved"
        )
        await edit_ui(message, "🎭 Dynamic Profile", help_text, parse_mode=enums.ParseMode.HTML)

# =================================================================================================
# 📘 HELP
# =================================================================================================

modules_help["ai_gems"] = {
    "gem learn [user] [limit]": "🧬 Deep Clone Chat Style",
    "gem list": "📚 Show All Gems",
    "gem create [name] [prompt]": "💾 Manually Save Gem",
    "gem delete [name]": "🗑️ Delete Custom Gem",
    "gem gen [topic]": "🔮 Auto-Generate Gem",
    "gem analyze [reply]": "🕵️ Simple Clone (1 Msg)",
    "gem use [name]": "✅ Set DM Persona",
    "gai [query]": "🧠 One-Shot AI Question",
    "gai dm [on/off]": "📨 Auto-Reply DMs",
    "gai chat [gem]": "⚔️ Auto-Reply Group",
    "gai stalk [user] [gem]": "🌍 Global Auto-Reply",
    "gai bot [user] [gem]": "🤖 Target Bot (Chat)",
    "gai summary [limit]": "📝 Summarize Chat",
    "gai status": "📊 System Status",
    "gai stop [all]": "🛑 Stop Chat / Kill All",
    "gai wipe": "🧹 Clear History",
    "img gen [prompt]": "🎨 Generate AI Image",
    "img surprise [topic]": "🎲 AI Dreams up Pic",
    "img chaos": "🌪️ Random Settings + Random Prompt",
    "img models": "📋 Show All Available Models",
    "img config [model] [size] [count] [quality] [style]": "⚙️ Configure Image Settings",
    "img random": "🎲 Randomize Settings Only",
    "img enhance [prompt]": "✨ AI-Enhance Your Prompt",
    "img setup": "🔧 Setup Image API",
    "img cache": "🗑️ Clear Generation Cache",
    "profile update": "🎭 Update all profile elements now",
    "profile name": "🎭 Generate new name only",
    "profile bio": "🎭 Generate new bio only", 
    "profile pfp": "🎭 Generate new profile picture only",
    "profile auto [on|off|status]": "🤖 Control automatic updates",
    "profile interval [hours]": "⏰ Set update interval",
    "profile history [names|bios|pfps]": "📜 View profile history",
    "api status": "📊 Show API Usage Statistics",
    "api health": "🔍 Check API Health",
    "api reset [type]": "🔄 Reset Usage Stats",
    "api config [key] [value]": "⚙️ Update API Configuration",
    "auto-enhance [on/off/status]": "✍️ Toggle auto message enhancement (fixes mistakes, improves clarity)",
}