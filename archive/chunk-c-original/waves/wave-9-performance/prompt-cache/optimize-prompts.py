#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  PROMPT CACHE OPTIMIZER — Restructure for Maximum Cache Hits                       ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import structlog

logger = structlog.get_logger()

@dataclass
class PromptAnalysis:
    agent: str
    original_length: int
    static_length: int
    dynamic_length: int
    cache_potential: float  # Percentage of prompt that can be cached
    optimized_template: str

def analyze_agent_prompt(agent_path: Path) -> Optional[PromptAnalysis]:
    """Analyze an agent YAML file and identify static vs dynamic sections."""
    try:
        with open(agent_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error("yaml_load_failed", path=str(agent_path), error=str(e))
        return None

    agent_name = agent_path.stem
    system_prompt = data.get("system_prompt", "")
    
    if not system_prompt:
        logger.warning("no_system_prompt", agent=agent_name)
        return None

    original_length = len(system_prompt)
    
    # Identify dynamic sections (variables, placeholders)
    dynamic_patterns = [
        r'\{\{[^}]+\}\}',  # Jinja2 variables
        r'\{[^}]+\}',      # Python format strings
        r'\$\{[^}]+\}',    # Shell-style variables
        r'<[A-Z_]+>',      # Placeholder tokens
    ]
    
    dynamic_matches = []
    for pattern in dynamic_patterns:
        dynamic_matches.extend(re.findall(pattern, system_prompt))
    
    # Calculate static vs dynamic lengths
    dynamic_content = " ".join(dynamic_matches)
    dynamic_length = len(dynamic_content)
    static_length = original_length - dynamic_length
    
    cache_potential = (static_length / original_length * 100) if original_length > 0 else 0
    
    # Generate optimized template
    # Strategy: Move all static content to the beginning
    static_sections = []
    dynamic_sections = []
    
    # Split by common section markers
    sections = re.split(r'\n(?=#+\s|\*\*)', system_prompt)
    
    for section in sections:
        has_dynamic = any(re.search(p, section) for p in dynamic_patterns)
        if has_dynamic:
            dynamic_sections.append(section)
        else:
            static_sections.append(section)
    
    optimized = "# STATIC PREFIX (CACHEABLE)\n"
    optimized += "\n".join(static_sections)
    optimized += "\n\n# DYNAMIC SUFFIX\n"
    optimized += "\n".join(dynamic_sections)
    
    return PromptAnalysis(
        agent=agent_name,
        original_length=original_length,
        static_length=static_length,
        dynamic_length=dynamic_length,
        cache_potential=round(cache_potential, 1),
        optimized_template=optimized,
    )

def optimize_all_agents(agents_dir: Path, output_dir: Path) -> List[Dict]:
    """Analyze and optimize all agent prompts."""
    results = []
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for agent_file in agents_dir.glob("*.yml"):
        analysis = analyze_agent_prompt(agent_file)
        if analysis:
            results.append({
                "agent": analysis.agent,
                "original_length": analysis.original_length,
                "static_length": analysis.static_length,
                "dynamic_length": analysis.dynamic_length,
                "cache_potential_percent": analysis.cache_potential,
            })
            
            # Write optimized template
            optimized_path = output_dir / f"{analysis.agent}-optimized.txt"
            with open(optimized_path, 'w') as f:
                f.write(analysis.optimized_template)
            
            logger.info("agent_optimized",
                       agent=analysis.agent,
                       cache_potential=f"{analysis.cache_potential}%",
                       output=str(optimized_path))
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Prompt Cache Optimizer")
    parser.add_argument("--agents-dir", default="agents", help="Directory containing agent YAML files")
    parser.add_argument("--output-dir", default="optimized-prompts", help="Output directory for optimized templates")
    parser.add_argument("--report", default="prompt-optimization-report.json", help="Output report file")
    args = parser.parse_args()
    
    agents_dir = Path(args.agents_dir)
    output_dir = Path(args.output_dir)
    
    if not agents_dir.exists():
        logger.error("agents_dir_not_found", path=str(agents_dir))
        return
    
    results = optimize_all_agents(agents_dir, output_dir)
    
    # Calculate totals
    total_original = sum(r["original_length"] for r in results)
    total_static = sum(r["static_length"] for r in results)
    avg_cache_potential = sum(r["cache_potential_percent"] for r in results) / len(results) if results else 0
    
    report = {
        "agents_analyzed": len(results),
        "total_original_chars": total_original,
        "total_static_chars": total_static,
        "average_cache_potential_percent": round(avg_cache_potential, 1),
        "agents": results,
    }
    
    with open(args.report, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*60}")
    print("PROMPT CACHE OPTIMIZATION REPORT")
    print(f"{'='*60}")
    print(f"Agents analyzed: {len(results)}")
    print(f"Average cache potential: {avg_cache_potential:.1f}%")
    print(f"Report written to: {args.report}")
    print(f"Optimized templates in: {output_dir}")

if __name__ == "__main__":
    main()
