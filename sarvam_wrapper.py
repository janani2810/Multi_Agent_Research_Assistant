"""Sarvam API Wrapper - LangChain Compatible Interface

This wrapper provides a LangChain-compatible interface for the Sarvam API.
It allows seamless integration with existing LangChain code by mimicking
the ChatOpenAI interface while using Sarvam's models underneath.

Example:
    from sarvam_wrapper import SarvamLLM
    
    llm = SarvamLLM(
        api_key="your-sarvam-api-key",
        model="Sarvam-2B",
        temperature=0.5
    )
    
    response = llm.invoke("What is AI?")
    print(response.content)
"""

import requests
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SarvamResponse:
    """Response object that mimics LangChain's message structure"""
    content: str
    model: str = ""
    tokens_used: int = 0
    
    def __repr__(self) -> str:
        return f"SarvamResponse(content='{self.content[:50]}...', model='{self.model}')"


class SarvamLLM:
    """
    Wrapper for Sarvam API that provides LangChain-compatible interface.
    
    This class wraps the Sarvam API to work seamlessly with LangChain's
    agent and chain systems. It implements the invoke() method that
    LangChain expects from language models.
    
    Attributes:
        api_key (str): Sarvam API key
        model (str): Model name (e.g., "Sarvam-2B", "Sarvam-7B")
        temperature (float): Temperature for response generation (0-1)
        api_url (str): Base API endpoint
        timeout (int): Request timeout in seconds
        max_retries (int): Maximum number of retry attempts
    """
    
    # Sarvam API endpoint
    API_BASE_URL = "https://api.sarvam.ai/v1"
    
    # Available models
    AVAILABLE_MODELS = [
        "Sarvam-2B",
        "Sarvam-7B",
        "Sarvam-Instruct-2B-v0.5",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "Sarvam-2B",
        temperature: float = 0.5,
        max_tokens: int = 2000,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialize Sarvam LLM wrapper.
        
        Args:
            api_key: Sarvam API key. If not provided, reads from SARVAM_API_KEY env var
            model: Model name to use (default: "Sarvam-2B")
            temperature: Sampling temperature (0-1). Higher = more creative
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Number of retries for failed requests
            
        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "SARVAM_API_KEY not found. Please provide the api_key parameter "
                "or set the SARVAM_API_KEY environment variable."
            )
        
        if model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"Model '{model}' not in known models. "
                f"Available: {', '.join(self.AVAILABLE_MODELS)}"
            )
        
        self.model = model
        self.temperature = max(0.0, min(1.0, temperature))  # Clamp between 0-1
        self.max_tokens = max(1, min(4000, max_tokens))  # Clamp between 1-4000
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_url = f"{self.API_BASE_URL}/chat/completions"
        
        logger.info(
            f"Initialized SarvamLLM with model={model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare request headers for Sarvam API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SarvamLLM-Wrapper/1.0",
        }
    
    def _prepare_payload(self, prompt: str) -> Dict[str, Any]:
        """
        Prepare request payload for Sarvam API.
        
        Args:
            prompt: The input prompt/message
            
        Returns:
            Dictionary with API request payload
        """
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": 0.95,  # Nucleus sampling
            "top_k": 50,    # Top-k sampling
        }
    
    def _make_request(self, payload: Dict[str, Any]) -> requests.Response:
        """
        Make API request with retry logic.
        
        Args:
            payload: Request payload
            
        Returns:
            Response object
            
        Raises:
            Exception: If all retries fail
        """
        headers = self._prepare_headers()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API request attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                logger.warning(f"Timeout on attempt {attempt + 1}")
                
            except requests.exceptions.ConnectionError:
                last_error = "Connection error"
                logger.warning(f"Connection error on attempt {attempt + 1}")
                
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
                
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
            
            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        raise Exception(
            f"Sarvam API request failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )
    
    def _extract_content(self, response: requests.Response) -> tuple[str, int]:
        """
        Extract content and token count from API response.
        
        Args:
            response: API response object
            
        Returns:
            Tuple of (content, tokens_used)
            
        Raises:
            Exception: If response format is unexpected
        """
        try:
            data = response.json()
            
            # Extract message content
            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise Exception(
                    f"Unexpected API response format: {data}. "
                    f"Error: {e}"
                )
            
            # Extract token count (if available)
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            return content, tokens_used
            
        except requests.exceptions.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in API response: {e}")
    
    def invoke(self, prompt: str) -> SarvamResponse:
        """
        Call Sarvam API with the given prompt.
        
        This method is the main interface for LangChain compatibility.
        It takes a prompt and returns a response object.
        
        Args:
            prompt: Input prompt/message
            
        Returns:
            SarvamResponse with generated content
            
        Raises:
            ValueError: If prompt is invalid
            Exception: If API call fails
            
        Example:
            >>> llm = SarvamLLM()
            >>> response = llm.invoke("What is machine learning?")
            >>> print(response.content)
        """
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        
        logger.info(f"Invoking Sarvam API with prompt (length: {len(prompt)})")
        
        try:
            # Prepare request
            payload = self._prepare_payload(prompt)
            logger.debug(f"Payload: {payload}")
            
            # Make API request
            response = self._make_request(payload)
            
            # Extract content
            content, tokens_used = self._extract_content(response)
            
            logger.info(
                f"Successfully invoked Sarvam API. "
                f"Model: {self.model}, Tokens used: {tokens_used}"
            )
            
            return SarvamResponse(
                content=content,
                model=self.model,
                tokens_used=tokens_used,
            )
            
        except Exception as e:
            logger.error(f"Sarvam API error: {str(e)}")
            raise Exception(f"Sarvam API error: {str(e)}")
    
    def __call__(self, prompt: str) -> SarvamResponse:
        """
        Allow using the object as a callable.
        
        Example:
            >>> llm = SarvamLLM()
            >>> response = llm("Hello, how are you?")
        """
        return self.invoke(prompt)
    
    def batch_invoke(self, prompts: List[str]) -> List[SarvamResponse]:
        """
        Invoke API with multiple prompts.
        
        Args:
            prompts: List of prompts
            
        Returns:
            List of SarvamResponse objects
            
        Example:
            >>> llm = SarvamLLM()
            >>> responses = llm.batch_invoke(["What is AI?", "What is ML?"])
        """
        logger.info(f"Batch invoking with {len(prompts)} prompts")
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                response = self.invoke(prompt)
                results.append(response)
                logger.debug(f"Processed prompt {i + 1}/{len(prompts)}")
            except Exception as e:
                logger.error(f"Error processing prompt {i + 1}: {e}")
                results.append(
                    SarvamResponse(
                        content=f"Error: {str(e)}",
                        model=self.model,
                        tokens_used=0,
                    )
                )
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "api_url": self.api_url,
            "available_models": self.AVAILABLE_MODELS,
        }
    
    def update_config(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        Update configuration parameters.
        
        Args:
            temperature: New temperature value
            max_tokens: New max tokens value
            model: New model name
            
        Example:
            >>> llm = SarvamLLM()
            >>> llm.update_config(temperature=0.7, max_tokens=1500)
        """
        if temperature is not None:
            self.temperature = max(0.0, min(1.0, temperature))
            logger.info(f"Updated temperature to {self.temperature}")
        
        if max_tokens is not None:
            self.max_tokens = max(1, min(4000, max_tokens))
            logger.info(f"Updated max_tokens to {self.max_tokens}")
        
        if model is not None:
            self.model = model
            logger.info(f"Updated model to {self.model}")
    
    def __repr__(self) -> str:
        return (
            f"SarvamLLM(model='{self.model}', "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens})"
        )
    
    def __str__(self) -> str:
        return f"SarvamLLM({self.model})"


# Singleton pattern for easy access
_sarvam_instance: Optional[SarvamLLM] = None


def get_sarvam_llm(
    api_key: Optional[str] = None,
    model: str = "Sarvam-2B",
    temperature: float = 0.5,
    **kwargs
) -> SarvamLLM:
    """
    Get or create a SarvamLLM instance (singleton pattern).
    
    Args:
        api_key: Sarvam API key
        model: Model name
        temperature: Temperature setting
        **kwargs: Additional arguments for SarvamLLM
        
    Returns:
        SarvamLLM instance
        
    Example:
        >>> llm = get_sarvam_llm(temperature=0.7)
        >>> response = llm.invoke("Hello!")
    """
    global _sarvam_instance
    
    if _sarvam_instance is None:
        _sarvam_instance = SarvamLLM(
            api_key=api_key,
            model=model,
            temperature=temperature,
            **kwargs
        )
    
    return _sarvam_instance


def reset_sarvam_instance() -> None:
    """Reset the singleton instance. Useful for testing."""
    global _sarvam_instance
    _sarvam_instance = None


# Version info
__version__ = "1.0.0"
__author__ = "Multi-Agent Research Assistant"
__all__ = ["SarvamLLM", "SarvamResponse", "get_sarvam_llm", "reset_sarvam_instance"]


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Check if API key is set
    if not os.getenv("SARVAM_API_KEY"):
        print("Error: SARVAM_API_KEY environment variable not set")
        sys.exit(1)
    
    # Create instance
    llm = SarvamLLM(temperature=0.7)
    print(f"Created: {llm}")
    
    # Test invoke
    print("\nTesting invoke...")
    try:
        response = llm.invoke("What is artificial intelligence?")
        print(f"Response: {response.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")