"""
Model Configuration Module

Centralized configuration for LLaMA-2-7B model.
Reads from competition.yaml and provides defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ModelConfig:
    """Centralized model configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize model configuration.
        
        Args:
            config_path: Path to competition.yaml. If None, auto-detects.
        """
        self.config_path = self._find_config(config_path)
        self.config = self._load_config()
        self.ai_config = self.config.get('ai', {})
    
    def _find_config(self, config_path: Optional[str]) -> Path:
        """Find competition.yaml"""
        if config_path:
            return Path(config_path)
        
        # Check current directory
        current = Path.cwd()
        if (current / "competition.yaml").exists():
            return current / "competition.yaml"
        
        # Check sentinel-alpha directory
        sentinel_path = Path("/root/sentinel-alpha/competition.yaml")
        if sentinel_path.exists():
            return sentinel_path
        
        raise FileNotFoundError("competition.yaml not found")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config from {self.config_path}: {e}")
    
    @property
    def llm_enabled(self) -> bool:
        """Check if LLM is enabled"""
        return self.ai_config.get('llm_enabled', False)
    
    @property
    def llm_model_path(self) -> Path:
        """Get LLM model directory path"""
        path_str = self.ai_config.get('llm_model_path', '/opt/llm_models/llama-2-7b')
        return Path(path_str)
    
    @property
    def llm_model_file(self) -> str:
        """Get LLM model filename"""
        return self.ai_config.get('llm_model_file', 'llama-2-7b-chat.Q4_K_M.gguf')
    
    @property
    def llm_full_path(self) -> Path:
        """Get full path to LLM model file"""
        return self.llm_model_path / self.llm_model_file
    
    @property
    def llm_fallback_mode(self) -> str:
        """Get fallback behavior if LLM fails: 'continue' or 'halt'"""
        return self.ai_config.get('llm_fallback_mode', 'continue')
    
    @property
    def llm_n_threads(self) -> int:
        """Get number of threads for LLM inference"""
        return self.ai_config.get('llm_n_threads', 4)
    
    @property
    def llm_n_ctx(self) -> int:
        """Get context window size for LLM"""
        return self.ai_config.get('llm_n_ctx', 2048)
    
    def validate_model_exists(self) -> tuple:
        """
        Validate that model file exists and is readable.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.llm_enabled:
            return True, "LLM disabled in config"
        
        model_path = self.llm_full_path
        
        if not model_path.exists():
            return False, f"Model file not found: {model_path}"
        
        if not os.access(model_path, os.R_OK):
            return False, f"Model file not readable: {model_path}"
        
        # Check file size (should be > 1GB for 4-bit model)
        size_mb = model_path.stat().st_size / (1024 * 1024)
        if size_mb < 1000:
            return False, f"Model file too small ({size_mb:.1f}MB), may be corrupt"
        
        return True, f"Model valid: {model_path} ({size_mb:.1f}MB)"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information"""
        info = {
            'enabled': self.llm_enabled,
            'model_path': str(self.llm_full_path),
            'fallback_mode': self.llm_fallback_mode,
            'n_threads': self.llm_n_threads,
            'n_ctx': self.llm_n_ctx,
        }
        
        if self.llm_enabled:
            is_valid, message = self.validate_model_exists()
            info['valid'] = is_valid
            info['validation_message'] = message
            
            if is_valid and self.llm_full_path.exists():
                size_mb = self.llm_full_path.stat().st_size / (1024 * 1024)
                info['size_mb'] = round(size_mb, 1)
        
        return info


# Singleton instance
_model_config_instance: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """Get singleton model configuration instance"""
    global _model_config_instance
    if _model_config_instance is None:
        _model_config_instance = ModelConfig()
    return _model_config_instance


if __name__ == '__main__':
    # Test model configuration
    config = ModelConfig()
    print("Model Configuration:")
    print(f"  Enabled: {config.llm_enabled}")
    print(f"  Model Path: {config.llm_full_path}")
    print(f"  Fallback Mode: {config.llm_fallback_mode}")
    print(f"  Threads: {config.llm_n_threads}")
    print(f"  Context: {config.llm_n_ctx}")
    
    is_valid, message = config.validate_model_exists()
    print(f"\nValidation: {message}")
    
    print("\nFull Info:")
    import json
    print(json.dumps(config.get_model_info(), indent=2))
