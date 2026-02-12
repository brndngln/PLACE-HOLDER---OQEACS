import { useState } from "react";

const TIERS = {
  models: [
    {
      tier: "TITAN",
      label: "🏆 TITAN TIER — Frontier Open-Source (Server/Multi-GPU)",
      color: "#FFD700",
      bg: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
      models: [
        {
          name: "DeepSeek-V3.2",
          params: "685B (MoE)",
          active: "~37B active/token",
          license: "MIT (code) + DeepSeek License",
          sweBench: "~56-62%",
          context: "128K tokens",
          strengths: [
            "Rivals GPT-5 on reasoning benchmarks",
            "94.2% MMLU — ties proprietary models",
            "Sparse attention for long-context efficiency",
            "Best all-around open model for general + coding",
          ],
          deploy: "vLLM, SGLang, TRT-LLM · ollama run deepseek-v3",
          hardware: "8×H100 (FP8) or 4×H100 (INT4 quantized)",
          verdict: "👑 THE KING — Best general-purpose + coding open model",
        },
        {
          name: "Kimi K2.5",
          params: "1T (MoE, 384 experts)",
          active: "32B active/token",
          license: "Open weights (permissive)",
          sweBench: "65.8% (K2) → higher with K2.5",
          context: "128K → 256K (K2.5)",
          strengths: [
            "State-of-the-art SWE-bench for open models",
            "Native multimodal agentic model",
            "Trained explicitly for tool use + coding agents",
            "Outperforms GPT-4.1 on SWE-bench (65.8% vs 61.3%)",
          ],
          deploy: "vLLM, SGLang · Ollama (kimi-k2.5)",
          hardware: "8×H100 (192GB VRAM with INT4)",
          verdict: "🥇 #1 FOR CODING AGENTS — Purpose-built for agentic coding",
        },
        {
          name: "GLM-4.7",
          params: "Large MoE",
          active: "Variable",
          license: "Open weights",
          sweBench: "73.8% Verified / 91.2% (some benchmarks)",
          context: "128K tokens",
          strengths: [
            "Highest SWE-bench among all open models",
            "Interleaved + Preserved Thinking modes",
            "Superior terminal/CLI reasoning",
            "Ranks alongside closed models like GPT-5.1-codex",
          ],
          deploy: "vLLM, SGLang · Ollama (glm-4.7)",
          hardware: "Multi-GPU server setup",
          verdict: "🔥 CODING MONSTER — Highest SWE-bench open-source scores",
        },
        {
          name: "Qwen3-Coder-480B-A35B",
          params: "480B (MoE)",
          active: "35B active/token",
          license: "Apache 2.0",
          sweBench: "~65%+ (agentic scaffold)",
          context: "128K tokens",
          strengths: [
            "Purpose-built for agentic coding workflows",
            "Repository-scale understanding",
            "Trained for multi-file edits, git ops, test loops",
            "Apache 2.0 — fully permissive license",
          ],
          deploy: "vLLM, SGLang, TRT-LLM",
          hardware: "4-8× H100 GPUs",
          verdict: "⚡ AGENTIC CODER — Built specifically for AI coding agents",
        },
        {
          name: "gpt-oss-120B",
          params: "120B (dense)",
          active: "120B (all active)",
          license: "Permissive (OpenAI open-weight)",
          sweBench: "~65% (high reasoning mode)",
          context: "128K tokens",
          strengths: [
            "OpenAI's first open-weight model since GPT-2",
            "Matches o4-mini on core benchmarks",
            "Adjustable reasoning levels (low/med/high)",
            "Runs on single 80GB GPU (H100/MI300X)",
          ],
          deploy: "vLLM, llama.cpp, Ollama",
          hardware: "1× H100 80GB (or equivalent)",
          verdict: "🆕 OPENAI OPEN — Surprisingly capable single-GPU frontier model",
        },
      ],
    },
    {
      tier: "ELITE",
      label: "💎 ELITE TIER — High Performance (Workstation/Multi-GPU)",
      color: "#00D4FF",
      bg: "linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%)",
      models: [
        {
          name: "Devstral 2 (Mistral)",
          params: "~Large",
          active: "Full",
          license: "Apache 2.0",
          sweBench: "72.2%",
          context: "128K tokens",
          strengths: [
            "72.2% SWE-bench — frontier open-weight",
            "Built in collaboration with All Hands AI (OpenHands)",
            "Native OpenHands + SWE-Agent support",
            "Outperforms DeepSeek V3.2 in Cline coding tasks",
          ],
          deploy: "vLLM, SGLang, Mistral Vibe CLI",
          hardware: "Multi-GPU workstation",
          verdict: "🎯 PERFECT FIT — Co-built with OpenHands team",
        },
        {
          name: "Kimi-Dev-72B",
          params: "72B (dense)",
          active: "72B",
          license: "Open weights",
          sweBench: "60.4% Verified (SOTA at release)",
          context: "128K tokens",
          strengths: [
            "RL-trained to autonomously patch real codebases",
            "Runs in Docker, earns rewards only when tests pass",
            "State-of-the-art among 72B-class models",
            "Specialist for software engineering tasks",
          ],
          deploy: "vLLM, SGLang · Ollama",
          hardware: "2× RTX 4090 or 1× A100 80GB",
          verdict: "🔧 CODE SPECIALIST — Pure SWE model, Docker-native",
        },
        {
          name: "Qwen3-235B-A22B",
          params: "235B (MoE)",
          active: "22B active/token",
          license: "Apache 2.0 ✅",
          sweBench: "~55%+",
          context: "32K (131K with YaRN)",
          strengths: [
            "Flagship MoE — rivals DeepSeek-R1 and o3-mini",
            "Hybrid thinking mode (toggle reasoning on/off)",
            "119 languages supported",
            "Apache 2.0 — no restrictions whatsoever",
          ],
          deploy: "vLLM, SGLang · ollama run qwen3:235b",
          hardware: "4× H100 (FP8) or 2× with aggressive quant",
          verdict: "🌐 BEST LICENSE — Apache 2.0 powerhouse for your system",
        },
        {
          name: "DeepSeek-R1",
          params: "671B (MoE)",
          active: "~37B active",
          license: "MIT",
          sweBench: "~50-55%",
          context: "128K tokens",
          strengths: [
            "Groundbreaking chain-of-thought reasoning",
            "IMO 2025 & IOI 2025 gold medals",
            "Distilled variants available (1.5B → 70B)",
            "MIT license — fully free",
          ],
          deploy: "vLLM, SGLang · ollama run deepseek-r1",
          hardware: "8×H100 (full) or consumer GPU (distilled)",
          verdict: "🧠 REASONING GOD — Best for complex debugging logic",
        },
      ],
    },
    {
      tier: "ACCESSIBLE",
      label: "🚀 ACCESSIBLE TIER — Consumer Hardware (Single GPU)",
      color: "#00FF88",
      bg: "linear-gradient(135deg, #0d1117 0%, #0a1628 50%, #0d2137 100%)",
      models: [
        {
          name: "Devstral Small 2",
          params: "24B",
          active: "24B",
          license: "Apache 2.0 ✅",
          sweBench: "68.0%",
          context: "128K tokens",
          strengths: [
            "68% SWE-bench on just 24B params — insane efficiency",
            "Runs on single RTX 4090 or Mac 32GB RAM",
            "Apache 2.0 — zero restrictions",
            "Local agent experience on consumer hardware",
          ],
          deploy: "Ollama, vLLM, llama.cpp",
          hardware: "1× RTX 4090 24GB or Mac 32GB",
          verdict: "⭐ BEST BANG/BUCK — 68% SWE-bench on a single 4090!",
        },
        {
          name: "Qwen3-Coder-30B",
          params: "30B (MoE-style)",
          active: "~3B active",
          license: "Apache 2.0 ✅",
          sweBench: "~48% (within 20% of 480B version)",
          context: "32K+ tokens",
          strengths: [
            "Runs on AI PCs and consumer workstations",
            "Within 20% of the 480B version on SWE-bench",
            "Verified working with OpenHands by AMD",
            "Minimal VRAM footprint",
          ],
          deploy: "Ollama, vLLM, Lemonade (AMD)",
          hardware: "RTX 3090/4090 or equivalent",
          verdict: "🏠 EDGE CODING — Verified with OpenHands on consumer HW",
        },
        {
          name: "MiMo-V2-Flash (Xiaomi)",
          params: "Small MoE",
          active: "~fraction",
          license: "Open weights",
          sweBench: "Competitive with DeepSeek-V3.2",
          context: "128K tokens",
          strengths: [
            "Outperforms much larger models on SWE benchmarks",
            "~150 tokens/sec inference speed",
            "Trained for agentic + tool-calling workflows",
            "87% MMLU despite tiny size",
          ],
          deploy: "vLLM, SGLang",
          hardware: "Consumer GPU friendly",
          verdict: "🏎️ SPEED DEMON — Tiny but punches way above weight",
        },
        {
          name: "DeepCoder-14B",
          params: "14B",
          active: "14B",
          license: "Open source",
          sweBench: "~Good for size",
          context: "128K tokens",
          strengths: [
            "O3-mini level coding at 14B params",
            "1.5B variant also available",
            "Excellent for resource-constrained setups",
            "Strong reasoning chain for debugging",
          ],
          deploy: "Ollama · ollama run deepcoder",
          hardware: "8-16GB VRAM",
          verdict: "💡 LIGHTWEIGHT — O3-mini level on minimal hardware",
        },
        {
          name: "Qwen3-32B (Dense)",
          params: "32B",
          active: "32B",
          license: "Apache 2.0 ✅",
          sweBench: "~45%+",
          context: "32K tokens",
          strengths: [
            "Matches Qwen2.5-72B performance at half the size",
            "Hybrid thinking mode available",
            "Strong STEM, coding, and reasoning",
            "Apache 2.0 — fully permissive",
          ],
          deploy: "Ollama · ollama run qwen3:32b",
          hardware: "1× RTX 4090 24GB (Q4 quantized)",
          verdict: "🎖️ DENSE WORKHORSE — Best pure dense model for single GPU",
        },
      ],
    },
  ],
  agents: [
    {
      name: "OpenHands",
      role: "Your System 16 — AI Coder Alpha",
      status: "✅ KEEP — Top-tier choice",
      desc: "Leading open-source coding agent framework. #1 on SWE-bench with multiple models. Full autonomous development: write, edit, run, debug, browse, deploy.",
      strengths: ["65K+ GitHub stars", "Docker sandboxed execution", "Works with ANY LLM via LiteLLM", "Enterprise-ready (GitHub, GitLab, Slack integration)"],
      best_models: "GLM-4.7, Kimi K2.5, DeepSeek-V3.2, Devstral 2",
    },
    {
      name: "SWE-Agent",
      role: "Your System 17 — AI Coder Beta",
      status: "✅ KEEP — Specialized & proven",
      desc: "Purpose-built for navigating repos, finding bugs, writing patches. Issue-to-PR automation. Standardized scaffold used across SWE-bench evaluations.",
      strengths: ["Gold standard evaluation scaffold", "Issue→PR pipeline", "Works with open & closed models", "Proven on real GitHub issues"],
      best_models: "GLM-4.7, Kimi K2.5, DeepSeek-V3.2, DeepSeek-R1",
    },
    {
      name: "Cline",
      role: "🆕 RECOMMENDED — AI Coder Gamma",
      status: "⭐ ADD THIS — Most practical daily-use agent",
      desc: "VS Code-native coding agent with Plan Mode, MCP integration, and terminal-first controls. 5M+ installs. Works with cloud OR local models via Ollama.",
      strengths: ["Plan → Review → Execute workflow", "MCP tool protocol support", "Works with Ollama local models", "VS Code + JetBrains + CLI"],
      best_models: "Any — Devstral Small 2, Qwen3-32B, or cloud models",
    },
    {
      name: "Aider",
      role: "🆕 RECOMMENDED — AI Coder Delta",
      status: "⭐ ADD THIS — Best terminal pair-programmer",
      desc: "CLI-driven AI pair programmer. Multi-file editing via natural language. Git-aware diffs. Supports local models via Ollama for zero-cost coding.",
      strengths: ["Git-native (auto-commits)", "Multi-file refactoring", "Local model support (Ollama)", "Polyglot benchmark leader"],
      best_models: "Qwen3-235B, DeepSeek-V3.2, or local Qwen3-32B",
    },
    {
      name: "Roo Code",
      role: "🆕 OPTIONAL — AI Coder Epsilon",
      status: "🔄 CONSIDER — Multi-mode VS Code agent",
      desc: "Open-source VS Code extension with Orchestrator, Architect, Code, and Debug modes. Privacy-focused with .rooignore. Works fully offline with local models.",
      strengths: ["4 specialized modes", "Offline-capable", "Privacy-first (.rooignore)", "Understands entire codebases"],
      best_models: "Any local or cloud model",
    },
    {
      name: "Goose (by Block)",
      role: "🆕 OPTIONAL — AI Coder Zeta",
      status: "🔄 CONSIDER — Extensible agent framework",
      desc: "Open-source from Block (Square). Goes beyond coding — extensible, local-first agent that can write code, debug, interact with filesystem, and run tools.",
      strengths: ["Extensible plugin system", "Runs entirely locally", "Built by Block (enterprise-grade)", "Goes beyond just coding"],
      best_models: "Flexible — works with various providers",
    },
  ],
};

function ModelCard({ model, tierColor }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background: "rgba(255,255,255,0.04)",
        border: `1px solid ${expanded ? tierColor : "rgba(255,255,255,0.08)"}`,
        borderRadius: 12,
        padding: "16px 20px",
        cursor: "pointer",
        transition: "all 0.3s ease",
        marginBottom: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 18, fontWeight: 800, color: tierColor, fontFamily: "'JetBrains Mono', monospace" }}>
              {model.name}
            </span>
            <span style={{ fontSize: 11, background: "rgba(255,255,255,0.08)", padding: "2px 8px", borderRadius: 20, color: "#aaa" }}>
              {model.params}
            </span>
            {model.license.includes("Apache 2.0") && (
              <span style={{ fontSize: 10, background: "rgba(0,255,136,0.15)", color: "#00ff88", padding: "2px 8px", borderRadius: 20, fontWeight: 700 }}>
                APACHE 2.0
              </span>
            )}
            {model.license.includes("MIT") && (
              <span style={{ fontSize: 10, background: "rgba(0,200,255,0.15)", color: "#00c8ff", padding: "2px 8px", borderRadius: 20, fontWeight: 700 }}>
                MIT
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: "#e0e0e0", marginTop: 6, fontWeight: 600 }}>{model.verdict}</div>
        </div>
        <div style={{ textAlign: "right", minWidth: 100 }}>
          <div style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: 1 }}>SWE-bench</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: tierColor, fontFamily: "'JetBrains Mono', monospace" }}>
            {model.sweBench}
          </div>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 12 }}>
            <div>
              <div style={{ color: "#888", textTransform: "uppercase", letterSpacing: 1, fontSize: 10, marginBottom: 6 }}>Strengths</div>
              {model.strengths.map((s, i) => (
                <div key={i} style={{ color: "#c8c8c8", marginBottom: 4, paddingLeft: 12, position: "relative" }}>
                  <span style={{ position: "absolute", left: 0, color: tierColor }}>›</span> {s}
                </div>
              ))}
            </div>
            <div>
              <div style={{ color: "#888", textTransform: "uppercase", letterSpacing: 1, fontSize: 10, marginBottom: 6 }}>Specs</div>
              <div style={{ color: "#c8c8c8", marginBottom: 4 }}>
                <span style={{ color: "#666" }}>Active:</span> {model.active}
              </div>
              <div style={{ color: "#c8c8c8", marginBottom: 4 }}>
                <span style={{ color: "#666" }}>Context:</span> {model.context}
              </div>
              <div style={{ color: "#c8c8c8", marginBottom: 4 }}>
                <span style={{ color: "#666" }}>License:</span> {model.license}
              </div>
              <div style={{ color: "#c8c8c8", marginBottom: 8 }}>
                <span style={{ color: "#666" }}>Hardware:</span> {model.hardware}
              </div>
              <div style={{ color: "#888", textTransform: "uppercase", letterSpacing: 1, fontSize: 10, marginBottom: 6, marginTop: 12 }}>Deploy</div>
              <div style={{ color: "#c8c8c8", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, background: "rgba(0,0,0,0.3)", padding: "6px 10px", borderRadius: 6 }}>
                {model.deploy}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AgentCard({ agent }) {
  const isKeep = agent.status.includes("KEEP");
  const isAdd = agent.status.includes("ADD");
  const borderColor = isKeep ? "#00ff88" : isAdd ? "#FFD700" : "#00D4FF";

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.04)",
        border: `1px solid ${borderColor}40`,
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 12,
        padding: "16px 20px",
        marginBottom: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
        <div>
          <span style={{ fontSize: 17, fontWeight: 800, color: "#fff" }}>{agent.name}</span>
          <span style={{ fontSize: 12, color: "#888", marginLeft: 10 }}>{agent.role}</span>
        </div>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            padding: "3px 10px",
            borderRadius: 20,
            background: `${borderColor}20`,
            color: borderColor,
          }}
        >
          {agent.status}
        </span>
      </div>
      <div style={{ fontSize: 13, color: "#b0b0b0", marginTop: 8 }}>{agent.desc}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
        {agent.strengths.map((s, i) => (
          <span
            key={i}
            style={{
              fontSize: 11,
              padding: "3px 10px",
              borderRadius: 20,
              background: "rgba(255,255,255,0.06)",
              color: "#ccc",
            }}
          >
            {s}
          </span>
        ))}
      </div>
      <div style={{ fontSize: 11, color: "#888", marginTop: 10 }}>
        <span style={{ color: "#666" }}>Best LLMs for this agent:</span>{" "}
        <span style={{ color: borderColor }}>{agent.best_models}</span>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("models");
  const [expandAll, setExpandAll] = useState(false);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0a0f",
        color: "#e8e8e8",
        fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
        padding: "24px 16px",
      }}
    >
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              fontSize: 11,
              letterSpacing: 6,
              textTransform: "uppercase",
              color: "#555",
              marginBottom: 8,
            }}
          >
            Omni Quantum Elite AI Coding System
          </div>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 900,
              background: "linear-gradient(135deg, #FFD700, #00D4FF, #00FF88)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              lineHeight: 1.2,
              margin: 0,
            }}
          >
            Ultimate Open-Source LLM &amp; Agent Guide
          </h1>
          <div style={{ fontSize: 13, color: "#666", marginTop: 8 }}>
            100% Open Source · 100% Free · 100% Self-Hostable · Zero External Dependencies
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 24, background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 4 }}>
          {[
            { id: "models", label: "🧠 LLM Models", count: "14 models" },
            { id: "agents", label: "🤖 Coding Agents", count: "6 agents" },
            { id: "stack", label: "⚡ Recommended Stack", count: "3 tiers" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: "10px 8px",
                background: activeTab === tab.id ? "rgba(255,255,255,0.08)" : "transparent",
                border: "none",
                borderRadius: 8,
                color: activeTab === tab.id ? "#fff" : "#666",
                fontWeight: activeTab === tab.id ? 700 : 400,
                cursor: "pointer",
                transition: "all 0.2s",
                fontSize: 13,
              }}
            >
              {tab.label}
              <div style={{ fontSize: 10, color: "#555", marginTop: 2 }}>{tab.count}</div>
            </button>
          ))}
        </div>

        {/* Models Tab */}
        {activeTab === "models" && (
          <div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 20, padding: "12px 16px", background: "rgba(255,215,0,0.05)", border: "1px solid rgba(255,215,0,0.1)", borderRadius: 10 }}>
              <strong style={{ color: "#FFD700" }}>📊 Key Insight:</strong> Click any model to expand full details. All models below are open-source/open-weights, free to download, and self-hostable via <span style={{ color: "#00D4FF", fontFamily: "monospace" }}>Ollama</span>, <span style={{ color: "#00D4FF", fontFamily: "monospace" }}>vLLM</span>, <span style={{ color: "#00D4FF", fontFamily: "monospace" }}>SGLang</span>, or <span style={{ color: "#00D4FF", fontFamily: "monospace" }}>llama.cpp</span>.
            </div>

            {TIERS.models.map((tier) => (
              <div key={tier.tier} style={{ marginBottom: 28 }}>
                <h2 style={{ fontSize: 16, fontWeight: 800, color: tier.color, marginBottom: 12, letterSpacing: 0.5 }}>
                  {tier.label}
                </h2>
                {tier.models.map((model) => (
                  <ModelCard key={model.name} model={model} tierColor={tier.color} />
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Agents Tab */}
        {activeTab === "agents" && (
          <div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 20, padding: "12px 16px", background: "rgba(0,255,136,0.05)", border: "1px solid rgba(0,255,136,0.1)", borderRadius: 10 }}>
              <strong style={{ color: "#00FF88" }}>✅ Your Current Agents:</strong> OpenHands and SWE-Agent are excellent choices — <strong>keep them both</strong>. Below I've added recommended additions to make your system truly elite.
            </div>
            <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 20, background: "rgba(0,255,136,0.1)", color: "#00ff88", border: "1px solid rgba(0,255,136,0.2)" }}>
                🟢 KEEP = Already in your system
              </span>
              <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 20, background: "rgba(255,215,0,0.1)", color: "#FFD700", border: "1px solid rgba(255,215,0,0.2)" }}>
                🟡 ADD = Strongly recommended
              </span>
              <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 20, background: "rgba(0,212,255,0.1)", color: "#00D4FF", border: "1px solid rgba(0,212,255,0.2)" }}>
                🔵 CONSIDER = Optional enhancement
              </span>
            </div>

            {TIERS.agents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        )}

        {/* Stack Tab */}
        {activeTab === "stack" && (
          <div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 20, padding: "12px 16px", background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.1)", borderRadius: 10 }}>
              <strong style={{ color: "#00D4FF" }}>🏗️ Recommended Architecture:</strong> Use a tiered model strategy — route tasks to the right model based on complexity. Your Token Infinity System can intelligently distribute across these.
            </div>

            {/* Primary Stack */}
            <div style={{ background: "rgba(255,215,0,0.04)", border: "1px solid rgba(255,215,0,0.15)", borderRadius: 14, padding: 20, marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, color: "#FFD700", margin: "0 0 16px 0" }}>
                🏆 PRIMARY — Heavy Lifting (Server GPUs)
              </h3>
              <div style={{ fontSize: 13, color: "#ccc", lineHeight: 1.8 }}>
                <div style={{ marginBottom: 8 }}>
                  <strong style={{ color: "#FFD700" }}>For OpenHands (System 16):</strong> <span style={{ color: "#fff" }}>GLM-4.7</span> or <span style={{ color: "#fff" }}>Kimi K2.5</span>
                  <div style={{ fontSize: 11, color: "#888", paddingLeft: 16 }}>→ Highest SWE-bench scores, built for autonomous full-stack development</div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong style={{ color: "#FFD700" }}>For SWE-Agent (System 17):</strong> <span style={{ color: "#fff" }}>DeepSeek-V3.2</span> or <span style={{ color: "#fff" }}>DeepSeek-R1</span>
                  <div style={{ fontSize: 11, color: "#888", paddingLeft: 16 }}>→ Superior reasoning for bug hunting, deep logical analysis, precise patches</div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong style={{ color: "#FFD700" }}>For Cline (NEW System 18):</strong> <span style={{ color: "#fff" }}>Devstral 2</span> or <span style={{ color: "#fff" }}>Qwen3-Coder-480B</span>
                  <div style={{ fontSize: 11, color: "#888", paddingLeft: 16 }}>→ Agentic coding workflows, IDE-native, multi-file operations</div>
                </div>
                <div>
                  <strong style={{ color: "#FFD700" }}>For Aider (NEW System 19):</strong> <span style={{ color: "#fff" }}>Qwen3-235B-A22B</span>
                  <div style={{ fontSize: 11, color: "#888", paddingLeft: 16 }}>→ Fast pair-programming, Git-native diffs, Apache 2.0 license</div>
                </div>
              </div>
            </div>

            {/* Fallback Stack */}
            <div style={{ background: "rgba(0,212,255,0.04)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 14, padding: 20, marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, color: "#00D4FF", margin: "0 0 16px 0" }}>
                💎 FALLBACK — Failover &amp; Load Balancing
              </h3>
              <div style={{ fontSize: 13, color: "#ccc", lineHeight: 1.8 }}>
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: "#00D4FF" }}>•</span> <strong style={{ color: "#fff" }}>gpt-oss-120B</strong> — Single H100 fallback, adjustable reasoning
                </div>
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: "#00D4FF" }}>•</span> <strong style={{ color: "#fff" }}>Kimi-Dev-72B</strong> — Specialized SWE fallback
                </div>
                <div>
                  <span style={{ color: "#00D4FF" }}>•</span> <strong style={{ color: "#fff" }}>Devstral 2</strong> — Co-built with OpenHands team
                </div>
              </div>
            </div>

            {/* Edge Stack */}
            <div style={{ background: "rgba(0,255,136,0.04)", border: "1px solid rgba(0,255,136,0.15)", borderRadius: 14, padding: 20, marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, color: "#00FF88", margin: "0 0 16px 0" }}>
                🚀 EDGE — Consumer Hardware &amp; Fast Tasks
              </h3>
              <div style={{ fontSize: 13, color: "#ccc", lineHeight: 1.8 }}>
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: "#00FF88" }}>•</span> <strong style={{ color: "#fff" }}>Devstral Small 2 (24B)</strong> — 68% SWE-bench on a single 4090!
                </div>
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: "#00FF88" }}>•</span> <strong style={{ color: "#fff" }}>Qwen3-32B</strong> — Best dense model for single GPU
                </div>
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: "#00FF88" }}>•</span> <strong style={{ color: "#fff" }}>MiMo-V2-Flash</strong> — Ultra-fast, 150 tok/sec
                </div>
                <div>
                  <span style={{ color: "#00FF88" }}>•</span> <strong style={{ color: "#fff" }}>DeepCoder-14B</strong> — Minimal hardware, solid results
                </div>
              </div>
            </div>

            {/* Serving Infrastructure */}
            <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 14, padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, color: "#fff", margin: "0 0 16px 0" }}>
                🔧 Self-Hosting Infrastructure
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12 }}>
                {[
                  { name: "Ollama", desc: "Easiest local serving. One-command install. GGUF quantized models.", color: "#FFD700" },
                  { name: "vLLM", desc: "Production-grade serving. Highest throughput. Tensor parallelism.", color: "#00D4FF" },
                  { name: "SGLang", desc: "Fast inference engine. Great for MoE models. Structured generation.", color: "#00FF88" },
                  { name: "llama.cpp", desc: "CPU + GPU hybrid. Runs anywhere. Quantization king.", color: "#ff6b9d" },
                  { name: "LiteLLM", desc: "Unified API proxy. OpenAI-compatible. Route to any backend.", color: "#c084fc" },
                  { name: "LocalAI", desc: "OpenAI-compatible API server. Docker-native. Multiple backends.", color: "#fb923c" },
                ].map((tool) => (
                  <div key={tool.name} style={{ background: "rgba(0,0,0,0.3)", padding: "10px 14px", borderRadius: 8, borderLeft: `2px solid ${tool.color}` }}>
                    <div style={{ fontWeight: 700, color: tool.color, marginBottom: 4, fontFamily: "monospace" }}>{tool.name}</div>
                    <div style={{ color: "#999", fontSize: 11 }}>{tool.desc}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16, fontSize: 12, color: "#888", padding: "10px 14px", background: "rgba(255,255,255,0.03)", borderRadius: 8 }}>
                <strong style={{ color: "#FFD700" }}>💡 Token Infinity System Integration:</strong> Use <span style={{ color: "#c084fc" }}>LiteLLM</span> as your unified proxy layer. It provides an OpenAI-compatible API that can route to any local backend (Ollama, vLLM, SGLang) — perfect for your multi-tiered provider architecture with automatic failover and load balancing.
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 32, fontSize: 11, color: "#444", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: 16 }}>
          All models listed are open-source/open-weights, free to download, and fully self-hostable.
          <br />
          Data sourced from SWE-bench leaderboards, HuggingFace, and model documentation · Feb 2026
        </div>
      </div>
    </div>
  );
}
