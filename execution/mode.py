import os
import yaml
from pathlib import Path


class ExecutionMode:
    DRY_RUN = "dry_run"
    COMPETITION = "competition"
    LIVE = "live"


def get_config_path():
    """Find competition.yaml in current directory or parent"""
    current = Path.cwd()
    if (current / "competition.yaml").exists():
        return current / "competition.yaml"
    # Check sentinel-alpha directory
    sentinel_path = Path("/root/sentinel-alpha/competition.yaml")
    if sentinel_path.exists():
        return sentinel_path
    return None


def is_competition_mode():
    """Check if system is in competition mode"""
    config_path = get_config_path()
    if not config_path:
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('mode') == ExecutionMode.COMPETITION
    except Exception as e:
        print(f"Warning: Could not read competition mode: {e}")
        return False


def enforce_competition_mode(dry_run_requested: bool):
    """
    Enforce competition mode restrictions.
    
    Args:
        dry_run_requested: Whether dry_run=True was requested
        
    Returns:
        bool: Actual dry_run value to use (False in competition mode)
        
    Raises:
        RuntimeError: If dry_run=True is requested in competition mode
    """
    if is_competition_mode():
        if dry_run_requested:
            raise RuntimeError(
                "COMPETITION MODE ENFORCEMENT: dry_run=True is not allowed in competition mode. "
                "All trades must be real. To use dry run, change mode in competition.yaml to 'dry_run' or 'live'."
            )
        # Always return False (live trading) in competition mode
        return False
    
    # Not in competition mode, allow requested dry_run value
    return dry_run_requested


def validate_competition_readiness():
    """
    Validate system is ready for competition mode.
    
    Returns:
        tuple: (is_ready: bool, issues: list[str])
    """
    issues = []
    
    # Check config exists
    config_path = get_config_path()
    if not config_path:
        issues.append("competition.yaml not found")
        return False, issues
    
    # Check required environment variables
    required_env_vars = ['WEEX_API_KEY', 'WEEX_SECRET_KEY', 'WEEX_PASSPHRASE']
    for var in required_env_vars:
        if not os.getenv(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Check LLM model if enabled
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        ai_config = config.get('ai', {})
        if ai_config.get('llm_enabled'):
            model_path = Path(ai_config.get('llm_model_path', ''))
            model_file = ai_config.get('llm_model_file', '')
            full_path = model_path / model_file
            
            if not full_path.exists():
                issues.append(f"LLM model not found: {full_path}")
    except Exception as e:
        issues.append(f"Error reading config: {e}")
    
    return len(issues) == 0, issues
