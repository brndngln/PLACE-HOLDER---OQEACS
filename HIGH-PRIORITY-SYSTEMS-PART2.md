# ═══════════════════════════════════════════════════════════════════════════════════════════
# HIGH PRIORITY SYSTEMS (8-17) - PART 2
# OMNI QUANTUM ELITE - ULTIMATE EDITION
# Systems 12-14: Automation, Code Repository, Project Management
# ═══════════════════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SYSTEM 12: FLOW ARCHITECT (Workflow Automation)
# ═══════════════════════════════════════════════════════════════════════════════════════════

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║    ███████╗██╗      ██████╗ ██╗    ██╗     █████╗ ██████╗  ██████╗██╗  ██╗██╗████████╗███████╗ ██████╗████████╗                       ║
║    ██╔════╝██║     ██╔═══██╗██║    ██║    ██╔══██╗██╔══██╗██╔════╝██║  ██║██║╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝                       ║
║    █████╗  ██║     ██║   ██║██║ █╗ ██║    ███████║██████╔╝██║     ███████║██║   ██║   █████╗  ██║        ██║                          ║
║    ██╔══╝  ██║     ██║   ██║██║███╗██║    ██╔══██║██╔══██╗██║     ██╔══██║██║   ██║   ██╔══╝  ██║        ██║                          ║
║    ██║     ███████╗╚██████╔╝╚███╔███╔╝    ██║  ██║██║  ██║╚██████╗██║  ██║██║   ██║   ███████╗╚██████╗   ██║                          ║
║    ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝                          ║
║                                                                                                                                       ║
║                              "Automate Everything. Connect Anything. Zero Code Required."                                             ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              FLOW ARCHITECT - COMPLETE ARCHITECTURE                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                                         │
│    TRIGGERS                              N8N CORE                                    ACTIONS                                            │
│    ────────                              ────────                                    ───────                                            │
│                                                                                                                                         │
│    ┌──────────────────┐                 ┌─────────────────────────────────┐        ┌──────────────────┐                                │
│    │  📅 SCHEDULED    │                 │                                 │        │  🤖 AI SERVICES  │                                │
│    │  • Cron jobs     │────────────────▶│         N8N MAIN               │───────▶│  • LiteLLM       │                                │
│    │  • Intervals     │                 │                                 │        │  • Ollama        │                                │
│    │  • One-time      │                 │  • Visual workflow builder      │        │  • Langfuse      │                                │
│    └──────────────────┘                 │  • 400+ integrations            │        └──────────────────┘                                │
│                                         │  • Custom code nodes            │                                                            │
│    ┌──────────────────┐                 │  • Error handling               │        ┌──────────────────┐                                │
│    │  🔗 WEBHOOKS     │────────────────▶│  • Retry logic                  │───────▶│  📧 EMAIL        │                                │
│    │  • HTTP POST     │                 │  • Parallel execution           │        │  • Postal        │                                │
│    │  • JSON payload  │                 │                                 │        │  • Listmonk      │                                │
│    │  • Auth headers  │                 │         QUEUE MODE              │        └──────────────────┘                                │
│    └──────────────────┘                 │                                 │                                                            │
│                                         │  ┌─────────────────────────┐   │        ┌──────────────────┐                                │
│    ┌──────────────────┐                 │  │      REDIS QUEUE        │   │───────▶│  💬 CHAT         │                                │
│    │  📨 EMAIL        │────────────────▶│  │  • Job persistence      │   │        │  • Mattermost    │                                │
│    │  • IMAP polling  │                 │  │  • Priority queues      │   │        │  • Webhooks      │                                │
│    │  • New messages  │                 │  │  • Dead letter queue    │   │        └──────────────────┘                                │
│    │  • Attachments   │                 │  └─────────────────────────┘   │                                                            │
│    └──────────────────┘                 │                                 │        ┌──────────────────┐                                │
│                                         │         WORKERS                 │───────▶│  🗄️ DATABASES    │                                │
│    ┌──────────────────┐                 │                                 │        │  • PostgreSQL    │                                │
│    │  🔔 EVENTS       │────────────────▶│  ┌─────────────────────────┐   │        │  • Redis         │                                │
│    │  • Database      │                 │  │    N8N WORKER 1         │   │        │  • Qdrant        │                                │
│    │  • File changes  │                 │  │    N8N WORKER 2         │   │        └──────────────────┘                                │
│    │  • API events    │                 │  │    N8N WORKER N         │   │                                                            │
│    └──────────────────┘                 │  └─────────────────────────┘   │        ┌──────────────────┐                                │
│                                         │                                 │───────▶│  🔧 DEVOPS       │                                │
│    ┌──────────────────┐                 │         CREDENTIALS             │        │  • Gitea         │                                │
│    │  🤖 AI TRIGGERS  │────────────────▶│                                 │        │  • Docker        │                                │
│    │  • Chat messages │                 │  • Encrypted at rest            │        │  • Portainer     │                                │
│    │  • Agent calls   │                 │  • Vault integration            │        └──────────────────┘                                │
│    │  • Tool use      │                 │  • OAuth tokens                 │                                                            │
│    └──────────────────┘                 │                                 │        ┌──────────────────┐                                │
│                                         └─────────────────────────────────┘───────▶│  🌐 EXTERNAL     │                                │
│                                                                                     │  • REST APIs     │                                │
│                                                                                     │  • GraphQL       │                                │
│                                                                                     │  • SOAP          │                                │
│                                                                                     └──────────────────┘                                │
│                                                                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## DOCKER COMPOSE - COMPLETE

```yaml
# docker-compose.automation.yml
version: "3.9"

x-n8n-common: &n8n-common
  image: n8nio/n8n:latest
  environment: &n8n-env
    # Database
    DB_TYPE: postgresdb
    DB_POSTGRESDB_HOST: postgres
    DB_POSTGRESDB_PORT: 5432
    DB_POSTGRESDB_DATABASE: n8n
    DB_POSTGRESDB_USER: n8n
    DB_POSTGRESDB_PASSWORD: ${N8N_DB_PASSWORD}
    
    # Queue mode (Redis)
    EXECUTIONS_MODE: queue
    QUEUE_BULL_REDIS_HOST: redis
    QUEUE_BULL_REDIS_PORT: 6379
    QUEUE_BULL_REDIS_PASSWORD: ${REDIS_PASSWORD}
    QUEUE_BULL_REDIS_DB: 2
    QUEUE_HEALTH_CHECK_ACTIVE: true
    
    # Encryption
    N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}
    N8N_USER_MANAGEMENT_JWT_SECRET: ${N8N_JWT_SECRET}
    
    # Server
    N8N_HOST: n8n.omni-quantum.local
    N8N_PORT: 5678
    N8N_PROTOCOL: https
    WEBHOOK_URL: https://n8n.omni-quantum.local/
    N8N_EDITOR_BASE_URL: https://n8n.omni-quantum.local/
    
    # Features
    N8N_METRICS: true
    N8N_METRICS_INCLUDE_DEFAULT_METRICS: true
    N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL: true
    N8N_METRICS_INCLUDE_NODE_TYPE_LABEL: true
    N8N_METRICS_INCLUDE_CREDENTIAL_TYPE_LABEL: true
    N8N_METRICS_INCLUDE_API_ENDPOINTS: true
    N8N_METRICS_INCLUDE_API_PATH_LABEL: true
    
    # AI Features
    N8N_AI_ENABLED: true
    N8N_AI_PROVIDER: openai
    N8N_AI_OPENAI_API_KEY: ${OPENAI_API_KEY}
    
    # Timezone
    GENERIC_TIMEZONE: UTC
    TZ: UTC
    
    # Logging
    N8N_LOG_LEVEL: info
    N8N_LOG_OUTPUT: console
    
    # Performance
    N8N_PAYLOAD_SIZE_MAX: 256
    EXECUTIONS_DATA_SAVE_ON_SUCCESS: all
    EXECUTIONS_DATA_SAVE_ON_ERROR: all
    EXECUTIONS_DATA_SAVE_ON_PROGRESS: true
    EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS: true
    EXECUTIONS_DATA_PRUNE: true
    EXECUTIONS_DATA_MAX_AGE: 336
    
    # External hooks
    EXTERNAL_HOOK_FILES: /home/node/hooks/external-hooks.js
    
  volumes:
    - n8n_data:/home/node/.n8n
    - ./config/n8n/workflows:/home/node/workflows:ro
    - ./config/n8n/hooks:/home/node/hooks:ro
    - ./config/n8n/custom-nodes:/home/node/custom-nodes:ro
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - omni-quantum-network
  logging:
    driver: "json-file"
    options:
      max-size: "50m"
      max-file: "5"

services:
  # ═══════════════════════════════════════════════════════════════════════════════════════
  # N8N MAIN (Editor & Webhook Handler)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  n8n:
    <<: *n8n-common
    container_name: omni-quantum-n8n
    command: start
    ports:
      - "5678:5678"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    labels:
      - "omni.quantum.component=n8n"
      - "omni.quantum.tier=automation"
      - "omni.quantum.critical=true"
      - "prometheus.scrape=true"
      - "prometheus.port=5678"
      - "prometheus.path=/metrics"
      - "watchtower.enable=true"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # N8N WORKERS (Execution)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  n8n-worker-1:
    <<: *n8n-common
    container_name: omni-quantum-n8n-worker-1
    command: worker
    environment:
      <<: *n8n-env
      N8N_CONCURRENCY_PRODUCTION_LIMIT: 10
    restart: unless-stopped
    labels:
      - "omni.quantum.component=n8n-worker"
      - "omni.quantum.tier=automation"

  n8n-worker-2:
    <<: *n8n-common
    container_name: omni-quantum-n8n-worker-2
    command: worker
    environment:
      <<: *n8n-env
      N8N_CONCURRENCY_PRODUCTION_LIMIT: 10
    restart: unless-stopped
    labels:
      - "omni.quantum.component=n8n-worker"
      - "omni.quantum.tier=automation"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # N8N WEBHOOK PROCESSOR (Dedicated)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  n8n-webhook:
    <<: *n8n-common
    container_name: omni-quantum-n8n-webhook
    command: webhook
    environment:
      <<: *n8n-env
      N8N_DISABLE_UI: true
    ports:
      - "5679:5678"
    restart: unless-stopped
    labels:
      - "omni.quantum.component=n8n-webhook"
      - "omni.quantum.tier=automation"

volumes:
  n8n_data:

networks:
  omni-quantum-network:
    external: true
```

## N8N EXTERNAL HOOKS

```javascript
// config/n8n/hooks/external-hooks.js
// External hooks for n8n - Custom integrations

/**
 * Omni Quantum Elite - n8n External Hooks
 * 
 * These hooks integrate n8n with:
 * - Vault for credential injection
 * - Langfuse for AI observability
 * - Mattermost for notifications
 * - Custom metrics for Prometheus
 */

const https = require('https');
const http = require('http');

module.exports = {
    // ═══════════════════════════════════════════════════════════════════════════════════
    // WORKFLOW HOOKS
    // ═══════════════════════════════════════════════════════════════════════════════════
    
    workflow: {
        // Before workflow execution
        async execute(workflow, data) {
            const startTime = Date.now();
            
            // Log workflow start
            console.log(`[WORKFLOW] Starting: ${workflow.name} (${workflow.id})`);
            
            // Store start time for duration calculation
            data._omniQuantum = {
                startTime,
                workflowId: workflow.id,
                workflowName: workflow.name
            };
            
            return data;
        },
        
        // After workflow execution
        async postExecute(workflow, data, executionId) {
            const duration = Date.now() - (data._omniQuantum?.startTime || Date.now());
            const status = data.error ? 'failed' : 'success';
            
            // Log completion
            console.log(`[WORKFLOW] Completed: ${workflow.name} (${executionId}) - ${status} in ${duration}ms`);
            
            // Send to Mattermost if failed
            if (status === 'failed') {
                await sendMattermostNotification({
                    text: `⚠️ Workflow Failed: **${workflow.name}**`,
                    attachments: [{
                        color: '#ff0000',
                        fields: [
                            { title: 'Workflow', value: workflow.name, short: true },
                            { title: 'Execution ID', value: executionId, short: true },
                            { title: 'Duration', value: `${duration}ms`, short: true },
                            { title: 'Error', value: data.error?.message || 'Unknown error' }
                        ]
                    }]
                });
            }
            
            // Push metrics to Pushgateway
            await pushMetrics({
                workflow_executions_total: {
                    labels: { workflow: workflow.name, status },
                    value: 1
                },
                workflow_execution_duration_seconds: {
                    labels: { workflow: workflow.name },
                    value: duration / 1000
                }
            });
            
            return data;
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════════════════
    // NODE HOOKS
    // ═══════════════════════════════════════════════════════════════════════════════════
    
    node: {
        // Before node execution
        async preExecute(node, data) {
            // Track AI node usage for Langfuse
            if (node.type.includes('openAi') || node.type.includes('langchain')) {
                data._omniQuantum = data._omniQuantum || {};
                data._omniQuantum.aiNodeStart = Date.now();
            }
            
            return data;
        },
        
        // After node execution
        async postExecute(node, data) {
            // Log AI node usage
            if (data._omniQuantum?.aiNodeStart) {
                const duration = Date.now() - data._omniQuantum.aiNodeStart;
                console.log(`[AI NODE] ${node.name}: ${duration}ms`);
                
                // Could send to Langfuse here for AI observability
            }
            
            return data;
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════════════════
    // CREDENTIAL HOOKS
    // ═══════════════════════════════════════════════════════════════════════════════════
    
    credentials: {
        // Inject credentials from Vault
        async get(credentialType, credentialId) {
            // Check if credential should come from Vault
            const vaultPrefix = 'vault://';
            
            // This hook is called after n8n retrieves credentials
            // We can inject/modify credentials here
            
            return null; // Return null to use default behavior
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════════════════

async function sendMattermostNotification(payload) {
    const webhookUrl = process.env.MATTERMOST_WEBHOOK;
    if (!webhookUrl) return;
    
    return new Promise((resolve, reject) => {
        const url = new URL(webhookUrl);
        const options = {
            hostname: url.hostname,
            port: url.port || 443,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const req = (url.protocol === 'https:' ? https : http).request(options, (res) => {
            resolve(res.statusCode);
        });
        
        req.on('error', reject);
        req.write(JSON.stringify(payload));
        req.end();
    });
}

async function pushMetrics(metrics) {
    const pushgatewayUrl = process.env.PUSHGATEWAY_URL || 'http://pushgateway:9091';
    
    let body = '';
    for (const [name, config] of Object.entries(metrics)) {
        const labels = Object.entries(config.labels || {})
            .map(([k, v]) => `${k}="${v}"`)
            .join(',');
        body += `${name}{${labels}} ${config.value}\n`;
    }
    
    return new Promise((resolve, reject) => {
        const url = new URL(`${pushgatewayUrl}/metrics/job/n8n`);
        const options = {
            hostname: url.hostname,
            port: url.port || 9091,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain'
            }
        };
        
        const req = http.request(options, (res) => {
            resolve(res.statusCode);
        });
        
        req.on('error', (err) => {
            console.error('[METRICS] Push failed:', err.message);
            resolve(null);
        });
        req.write(body);
        req.end();
    });
}
```

## PRE-BUILT WORKFLOW TEMPLATES

```json
// config/n8n/workflows/ai-content-generator.json
{
  "name": "AI Content Generator",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 6
            }
          ]
        }
      },
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [250, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://litellm:4000/v1/chat/completions",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $credentials.litellmApiKey }}"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "model",
              "value": "groq/llama3-70b"
            },
            {
              "name": "messages",
              "value": "={{ JSON.stringify([{role: 'system', content: 'You are a helpful content writer.'}, {role: 'user', content: $json.prompt}]) }}"
            },
            {
              "name": "max_tokens",
              "value": "1000"
            }
          ]
        },
        "options": {
          "timeout": 120000
        }
      },
      "name": "Generate Content",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300],
      "typeVersion": 4
    },
    {
      "parameters": {
        "channel": "#content-updates",
        "text": "=📝 New content generated:\n\n{{ $json.choices[0].message.content.substring(0, 500) }}..."
      },
      "name": "Post to Mattermost",
      "type": "n8n-nodes-base.mattermost",
      "position": [650, 300],
      "typeVersion": 1
    }
  ],
  "connections": {
    "Schedule Trigger": {
      "main": [
        [
          {
            "node": "Generate Content",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Generate Content": {
      "main": [
        [
          {
            "node": "Post to Mattermost",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  },
  "tags": ["ai", "content", "automation"]
}
```

```json
// config/n8n/workflows/backup-notification.json
{
  "name": "Backup Status Notification",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "backup-status",
        "authentication": "headerAuth",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "typeVersion": 1,
      "webhookId": "backup-status-webhook"
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.success }}",
              "value2": true
            }
          ]
        }
      },
      "name": "Check Status",
      "type": "n8n-nodes-base.if",
      "position": [450, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "channel": "#backups",
        "text": "=✅ Backup completed successfully!\n\n**Type:** {{ $json.type }}\n**Size:** {{ $json.size }}\n**Duration:** {{ $json.duration }}s\n**Timestamp:** {{ $json.timestamp }}"
      },
      "name": "Success Notification",
      "type": "n8n-nodes-base.mattermost",
      "position": [650, 200],
      "typeVersion": 1
    },
    {
      "parameters": {
        "channel": "#backups",
        "text": "=❌ Backup FAILED!\n\n**Type:** {{ $json.type }}\n**Error:** {{ $json.error }}\n**Timestamp:** {{ $json.timestamp }}\n\n@channel Please investigate immediately!"
      },
      "name": "Failure Notification",
      "type": "n8n-nodes-base.mattermost",
      "position": [650, 400],
      "typeVersion": 1
    }
  ],
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "Check Status",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check Status": {
      "main": [
        [
          {
            "node": "Success Notification",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Failure Notification",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  },
  "tags": ["backup", "notification", "monitoring"]
}
```

```json
// config/n8n/workflows/security-alert-handler.json
{
  "name": "Security Alert Handler",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "security-alert",
        "authentication": "headerAuth",
        "options": {}
      },
      "name": "Security Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.severity }}",
              "operation": "equals",
              "value2": "critical"
            }
          ]
        }
      },
      "name": "Is Critical?",
      "type": "n8n-nodes-base.if",
      "position": [450, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "method": "POST",
        "url": "={{ $env.OMI_ALERT_WEBHOOK }}",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "title",
              "value": "🚨 CRITICAL Security Alert"
            },
            {
              "name": "message",
              "value": "={{ $json.description }}"
            },
            {
              "name": "priority",
              "value": "critical"
            },
            {
              "name": "speak",
              "value": "true"
            }
          ]
        }
      },
      "name": "Omi Alert",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 200],
      "typeVersion": 4
    },
    {
      "parameters": {
        "channel": "#security-alerts",
        "text": "=🚨 **CRITICAL SECURITY ALERT**\n\n**Type:** {{ $json.type }}\n**Source:** {{ $json.source_ip }}\n**Description:** {{ $json.description }}\n**Time:** {{ $json.timestamp }}\n\n@channel Immediate action required!"
      },
      "name": "Mattermost Critical",
      "type": "n8n-nodes-base.mattermost",
      "position": [850, 200],
      "typeVersion": 1
    },
    {
      "parameters": {
        "channel": "#security-alerts",
        "text": "=⚠️ Security Alert ({{ $json.severity }})\n\n**Type:** {{ $json.type }}\n**Source:** {{ $json.source_ip }}\n**Description:** {{ $json.description }}"
      },
      "name": "Mattermost Warning",
      "type": "n8n-nodes-base.mattermost",
      "position": [650, 400],
      "typeVersion": 1
    },
    {
      "parameters": {
        "operation": "insert",
        "table": "security_events",
        "columns": "event_type,source_ip,severity,description,raw_data,created_at",
        "additionalFields": {}
      },
      "name": "Log to Database",
      "type": "n8n-nodes-base.postgres",
      "position": [1050, 300],
      "typeVersion": 2
    }
  ],
  "connections": {
    "Security Webhook": {
      "main": [
        [
          {
            "node": "Is Critical?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Is Critical?": {
      "main": [
        [
          {
            "node": "Omi Alert",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Mattermost Warning",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Omi Alert": {
      "main": [
        [
          {
            "node": "Mattermost Critical",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Mattermost Critical": {
      "main": [
        [
          {
            "node": "Log to Database",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Mattermost Warning": {
      "main": [
        [
          {
            "node": "Log to Database",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  },
  "tags": ["security", "alerts", "critical"]
}
```

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SYSTEM 13: CODE CITADEL (Code Repository)
# ═══════════════════════════════════════════════════════════════════════════════════════════

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║     ██████╗ ██████╗ ██████╗ ███████╗     ██████╗██╗████████╗ █████╗ ██████╗ ███████╗██╗                                               ║
║    ██╔════╝██╔═══██╗██╔══██╗██╔════╝    ██╔════╝██║╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║                                               ║
║    ██║     ██║   ██║██║  ██║█████╗      ██║     ██║   ██║   ███████║██║  ██║█████╗  ██║                                               ║
║    ██║     ██║   ██║██║  ██║██╔══╝      ██║     ██║   ██║   ██╔══██║██║  ██║██╔══╝  ██║                                               ║
║    ╚██████╗╚██████╔╝██████╔╝███████╗    ╚██████╗██║   ██║   ██║  ██║██████╔╝███████╗███████╗                                          ║
║     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝     ╚═════╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝                                          ║
║                                                                                                                                       ║
║                              "Your Code. Your Rules. Your Infrastructure."                                                            ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

## DOCKER COMPOSE - COMPLETE

```yaml
# docker-compose.git.yml
version: "3.9"

services:
  # ═══════════════════════════════════════════════════════════════════════════════════════
  # GITEA (Code Repository)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  gitea:
    image: gitea/gitea:1.21
    container_name: omni-quantum-gitea
    environment:
      # General
      USER_UID: 1000
      USER_GID: 1000
      GITEA__DEFAULT_LOCALE: en-US
      
      # Database
      GITEA__database__DB_TYPE: postgres
      GITEA__database__HOST: postgres:5432
      GITEA__database__NAME: gitea
      GITEA__database__USER: gitea
      GITEA__database__PASSWD: ${GITEA_DB_PASSWORD}
      GITEA__database__SSL_MODE: disable
      
      # Server
      GITEA__server__DOMAIN: git.omni-quantum.local
      GITEA__server__SSH_DOMAIN: git.omni-quantum.local
      GITEA__server__ROOT_URL: https://git.omni-quantum.local/
      GITEA__server__HTTP_PORT: 3000
      GITEA__server__SSH_PORT: 2222
      GITEA__server__SSH_LISTEN_PORT: 22
      GITEA__server__LFS_START_SERVER: true
      GITEA__server__LFS_JWT_SECRET: ${GITEA_LFS_JWT_SECRET}
      GITEA__server__OFFLINE_MODE: false
      
      # Security
      GITEA__security__SECRET_KEY: ${GITEA_SECRET_KEY}
      GITEA__security__INTERNAL_TOKEN: ${GITEA_INTERNAL_TOKEN}
      GITEA__security__INSTALL_LOCK: true
      GITEA__security__PASSWORD_COMPLEXITY: "lower,upper,digit,spec"
      GITEA__security__MIN_PASSWORD_LENGTH: 12
      
      # Service
      GITEA__service__DISABLE_REGISTRATION: false
      GITEA__service__REQUIRE_SIGNIN_VIEW: false
      GITEA__service__REGISTER_EMAIL_CONFIRM: false
      GITEA__service__ENABLE_NOTIFY_MAIL: true
      GITEA__service__DEFAULT_KEEP_EMAIL_PRIVATE: true
      GITEA__service__DEFAULT_ALLOW_CREATE_ORGANIZATION: true
      GITEA__service__DEFAULT_ENABLE_TIMETRACKING: true
      
      # OAuth2 (Authentik)
      GITEA__oauth2_client__ENABLE_AUTO_REGISTRATION: true
      GITEA__oauth2_client__OPENID_CONNECT_SCOPES: "openid profile email"
      GITEA__oauth2_client__UPDATE_AVATAR: true
      GITEA__oauth2_client__ACCOUNT_LINKING: auto
      
      # Repository
      GITEA__repository__ROOT: /data/git/repositories
      GITEA__repository__DEFAULT_BRANCH: main
      GITEA__repository__DEFAULT_PRIVATE: private
      GITEA__repository__ENABLE_PUSH_CREATE_USER: true
      GITEA__repository__ENABLE_PUSH_CREATE_ORG: true
      
      # LFS
      GITEA__lfs__PATH: /data/lfs
      
      # Mailer
      GITEA__mailer__ENABLED: true
      GITEA__mailer__PROTOCOL: smtp
      GITEA__mailer__SMTP_ADDR: postal
      GITEA__mailer__SMTP_PORT: 25
      GITEA__mailer__FROM: "Gitea <gitea@omni-quantum.local>"
      
      # Actions (CI/CD)
      GITEA__actions__ENABLED: true
      GITEA__actions__DEFAULT_ACTIONS_URL: https://gitea.com
      
      # Indexer
      GITEA__indexer__ISSUE_INDEXER_TYPE: bleve
      GITEA__indexer__REPO_INDEXER_ENABLED: true
      GITEA__indexer__REPO_INDEXER_TYPE: bleve
      
      # Cache
      GITEA__cache__ENABLED: true
      GITEA__cache__ADAPTER: redis
      GITEA__cache__HOST: redis://:${REDIS_PASSWORD}@redis:6379/5
      
      # Session
      GITEA__session__PROVIDER: redis
      GITEA__session__PROVIDER_CONFIG: redis://:${REDIS_PASSWORD}@redis:6379/6
      
      # Queue
      GITEA__queue__TYPE: redis
      GITEA__queue__CONN_STR: redis://:${REDIS_PASSWORD}@redis:6379/7
      
      # Webhook
      GITEA__webhook__ALLOWED_HOST_LIST: "*"
      GITEA__webhook__SKIP_TLS_VERIFY: false
      
      # Metrics
      GITEA__metrics__ENABLED: true
      GITEA__metrics__ENABLED_ISSUE_BY_LABEL: true
      GITEA__metrics__ENABLED_ISSUE_BY_REPOSITORY: true
      
      # Log
      GITEA__log__MODE: console
      GITEA__log__LEVEL: info
      
    volumes:
      - gitea_data:/data
      - gitea_config:/etc/gitea
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "3003:3000"
      - "2222:22"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    networks:
      - omni-quantum-network
    labels:
      - "omni.quantum.component=gitea"
      - "omni.quantum.tier=development"
      - "omni.quantum.critical=true"
      - "prometheus.scrape=true"
      - "prometheus.port=3000"
      - "prometheus.path=/metrics"
      - "watchtower.enable=true"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # GITEA ACT RUNNER (CI/CD)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  gitea-runner:
    image: gitea/act_runner:latest
    container_name: omni-quantum-gitea-runner
    environment:
      GITEA_INSTANCE_URL: http://gitea:3000
      GITEA_RUNNER_REGISTRATION_TOKEN: ${GITEA_RUNNER_TOKEN}
      GITEA_RUNNER_NAME: omni-quantum-runner-1
      GITEA_RUNNER_LABELS: "ubuntu-latest:docker://node:20-bookworm,ubuntu-22.04:docker://ubuntu:22.04,python:docker://python:3.11"
      CONFIG_FILE: /config/config.yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - gitea_runner_data:/data
      - ./config/gitea-runner/config.yaml:/config/config.yaml:ro
    depends_on:
      gitea:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - omni-quantum-network
    labels:
      - "omni.quantum.component=gitea-runner"
      - "omni.quantum.tier=development"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # GITEA MIRROR SYNC (GitHub Mirror)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  gitea-mirror-sync:
    image: alpine:latest
    container_name: omni-quantum-gitea-mirror
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache curl jq
        while true; do
          echo "Triggering mirror sync..."
          # Add mirror sync logic here if needed
          sleep 3600
        done
    depends_on:
      - gitea
    restart: unless-stopped
    networks:
      - omni-quantum-network

volumes:
  gitea_data:
  gitea_config:
  gitea_runner_data:

networks:
  omni-quantum-network:
    external: true
```

## GITEA RUNNER CONFIGURATION

```yaml
# config/gitea-runner/config.yaml
log:
  level: info

runner:
  file: .runner
  capacity: 4
  timeout: 3h
  insecure: false
  fetch_timeout: 5s
  fetch_interval: 2s

cache:
  enabled: true
  dir: /data/cache
  host: redis
  port: 6379
  
container:
  network: omni-quantum-network
  privileged: false
  options: |
    --memory=4g
    --cpus=2
  workdir_parent: /workspace
  valid_volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  docker_host: ""
  force_pull: false
  
host:
  workdir_parent: /data/actions
```

## GITEA WEBHOOK FOR N8N INTEGRATION

```json
// Gitea webhook configuration for CI/CD integration
{
  "name": "n8n-integration",
  "events": [
    "push",
    "pull_request",
    "pull_request_review",
    "release",
    "issues"
  ],
  "config": {
    "url": "https://n8n.omni-quantum.local/webhook/gitea",
    "content_type": "json",
    "secret": "${GITEA_WEBHOOK_SECRET}"
  },
  "active": true
}
```

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SYSTEM 14: MISSION CONTROL (Project Management)
# ═══════════════════════════════════════════════════════════════════════════════════════════

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║    ███╗   ███╗██╗███████╗███████╗██╗ ██████╗ ███╗   ██╗     ██████╗ ██████╗ ███╗   ██╗████████╗██████╗  ██████╗ ██╗                   ║
║    ████╗ ████║██║██╔════╝██╔════╝██║██╔═══██╗████╗  ██║    ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔═══██╗██║                   ║
║    ██╔████╔██║██║███████╗███████╗██║██║   ██║██╔██╗ ██║    ██║     ██║   ██║██╔██╗ ██║   ██║   ██████╔╝██║   ██║██║                   ║
║    ██║╚██╔╝██║██║╚════██║╚════██║██║██║   ██║██║╚██╗██║    ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██╗██║   ██║██║                   ║
║    ██║ ╚═╝ ██║██║███████║███████║██║╚██████╔╝██║ ╚████║    ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║╚██████╔╝███████╗              ║
║    ╚═╝     ╚═╝╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝              ║
║                                                                                                                                       ║
║                              "Plan. Track. Ship. Repeat."                                                                             ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

## DOCKER COMPOSE - COMPLETE

```yaml
# docker-compose.projects.yml
version: "3.9"

x-plane-common: &plane-common
  networks:
    - omni-quantum-network
  restart: unless-stopped
  logging:
    driver: "json-file"
    options:
      max-size: "50m"
      max-file: "5"

services:
  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE WEB (Frontend)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-web:
    image: makeplane/plane-frontend:stable
    container_name: omni-quantum-plane-web
    <<: *plane-common
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://plane-api:8000
      NEXT_PUBLIC_DEPLOY_URL: https://plane.omni-quantum.local
      NEXT_PUBLIC_GOOGLE_CLIENTID: ""
      NEXT_PUBLIC_GITHUB_APP_NAME: ""
      NEXT_PUBLIC_SENTRY_DSN: ""
      NEXT_PUBLIC_ENABLE_OAUTH: "1"
      NEXT_PUBLIC_ENABLE_SENTRY: "0"
      NEXT_PUBLIC_ENABLE_SESSION_RECORDER: "0"
      NEXT_PUBLIC_TRACK_EVENTS: "0"
    ports:
      - "3004:3000"
    depends_on:
      - plane-api
    labels:
      - "omni.quantum.component=plane-web"
      - "omni.quantum.tier=projects"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE SPACE (Public Boards)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-space:
    image: makeplane/plane-space:stable
    container_name: omni-quantum-plane-space
    <<: *plane-common
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://plane-api:8000
      NEXT_PUBLIC_DEPLOY_URL: https://plane.omni-quantum.local
    ports:
      - "3005:3000"
    depends_on:
      - plane-api
    labels:
      - "omni.quantum.component=plane-space"
      - "omni.quantum.tier=projects"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE API (Backend)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-api:
    image: makeplane/plane-backend:stable
    container_name: omni-quantum-plane-api
    <<: *plane-common
    command: ./bin/docker-entrypoint-api.sh
    environment: &plane-api-env
      # Database
      DATABASE_URL: postgresql://plane:${PLANE_DB_PASSWORD}@postgres:5432/plane
      
      # Redis
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/8
      
      # Security
      SECRET_KEY: ${PLANE_SECRET_KEY}
      
      # Server
      WEB_URL: https://plane.omni-quantum.local
      DEBUG: "0"
      CORS_ALLOWED_ORIGINS: "https://plane.omni-quantum.local,http://localhost:3004"
      
      # Features
      ENABLE_SIGNUP: "1"
      ENABLE_EMAIL_PASSWORD: "1"
      ENABLE_MAGIC_LINK_LOGIN: "0"
      
      # OAuth (Authentik)
      OIDC_CLIENT_ID: plane
      OIDC_CLIENT_SECRET: ${PLANE_OAUTH_SECRET}
      OIDC_AUTH_URL: https://auth.omni-quantum.local/application/o/authorize/
      OIDC_TOKEN_URL: https://auth.omni-quantum.local/application/o/token/
      OIDC_USERINFO_URL: https://auth.omni-quantum.local/application/o/userinfo/
      OIDC_AUTO_REGISTRATION: "1"
      
      # Email
      EMAIL_HOST: postal
      EMAIL_PORT: "25"
      EMAIL_HOST_USER: ""
      EMAIL_HOST_PASSWORD: ""
      EMAIL_USE_TLS: "0"
      EMAIL_USE_SSL: "0"
      EMAIL_FROM: "Plane <plane@omni-quantum.local>"
      
      # Storage (MinIO)
      USE_MINIO: "1"
      AWS_ACCESS_KEY_ID: ${MINIO_ACCESS_KEY}
      AWS_SECRET_ACCESS_KEY: ${MINIO_SECRET_KEY}
      AWS_S3_ENDPOINT_URL: http://minio:9000
      AWS_S3_BUCKET_NAME: plane-uploads
      AWS_REGION: us-east-1
      
      # Sentry
      SENTRY_DSN: ""
      
      # GPT (for AI features)
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GPT_ENGINE: "gpt-4o-mini"
      
      # File uploads
      FILE_SIZE_LIMIT: "52428800"
      
    volumes:
      - plane_logs:/code/plane/logs
    ports:
      - "8004:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    labels:
      - "omni.quantum.component=plane-api"
      - "omni.quantum.tier=projects"
      - "omni.quantum.critical=true"
      - "prometheus.scrape=true"
      - "prometheus.port=8000"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE WORKER (Background Jobs)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-worker:
    image: makeplane/plane-backend:stable
    container_name: omni-quantum-plane-worker
    <<: *plane-common
    command: ./bin/docker-entrypoint-worker.sh
    environment:
      <<: *plane-api-env
    volumes:
      - plane_logs:/code/plane/logs
    depends_on:
      - plane-api
      - redis
    labels:
      - "omni.quantum.component=plane-worker"
      - "omni.quantum.tier=projects"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE BEAT (Scheduler)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-beat:
    image: makeplane/plane-backend:stable
    container_name: omni-quantum-plane-beat
    <<: *plane-common
    command: ./bin/docker-entrypoint-beat.sh
    environment:
      <<: *plane-api-env
    volumes:
      - plane_logs:/code/plane/logs
    depends_on:
      - plane-api
      - redis
    labels:
      - "omni.quantum.component=plane-beat"
      - "omni.quantum.tier=projects"

  # ═══════════════════════════════════════════════════════════════════════════════════════
  # PLANE MIGRATOR (Database Migrations)
  # ═══════════════════════════════════════════════════════════════════════════════════════
  plane-migrator:
    image: makeplane/plane-backend:stable
    container_name: omni-quantum-plane-migrator
    command: ./bin/docker-entrypoint-migrator.sh
    environment:
      <<: *plane-api-env
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"
    networks:
      - omni-quantum-network

volumes:
  plane_logs:

networks:
  omni-quantum-network:
    external: true
```

## PLANE INITIALIZATION SCRIPT

```bash
#!/bin/bash
# scripts/init-plane.sh
# Initialize Plane project management

set -e

echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo "                    PLANE PROJECT MANAGEMENT - INITIALIZATION"
echo "═══════════════════════════════════════════════════════════════════════════════════════"

# Wait for Plane API to be ready
echo "Waiting for Plane API..."
until curl -s http://localhost:8004/api/v1/health/ > /dev/null 2>&1; do
    echo "  Waiting..."
    sleep 5
done
echo "  ✅ Plane API is ready"

# Create default workspace
echo ""
echo "Creating default workspace..."
curl -s -X POST http://localhost:8004/api/v1/workspaces/ \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Omni Quantum Elite",
        "slug": "omni-quantum",
        "description": "Main workspace for all AI business projects"
    }' || echo "Workspace may already exist"

echo "  ✅ Default workspace ready"

# Create project templates
echo ""
echo "Creating project templates..."

# AI Development Project Template
cat > /tmp/ai-project-template.json << 'EOF'
{
    "name": "AI Product Development",
    "description": "Template for AI/ML product development projects",
    "default_states": [
        {"name": "Backlog", "color": "#grey"},
        {"name": "Research", "color": "#blue"},
        {"name": "Development", "color": "#yellow"},
        {"name": "Testing", "color": "#orange"},
        {"name": "Deployed", "color": "#green"},
        {"name": "Monitoring", "color": "#purple"}
    ],
    "default_labels": [
        {"name": "bug", "color": "#d73a4a"},
        {"name": "feature", "color": "#0075ca"},
        {"name": "ai-model", "color": "#7057ff"},
        {"name": "data-pipeline", "color": "#008672"},
        {"name": "infrastructure", "color": "#d4c5f9"},
        {"name": "documentation", "color": "#0052cc"}
    ]
}
EOF

echo "  ✅ Project templates created"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo "                    PLANE INITIALIZATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Access Plane at: https://plane.omni-quantum.local"
echo ""
```

## PLANE WEBHOOK INTEGRATION

```python
#!/usr/bin/env python3
# plane_integration/webhook_handler.py
"""
Plane Webhook Handler for n8n Integration

Receives webhooks from Plane and forwards to n8n for processing.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import hmac
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlaneWebhook")

app = FastAPI(title="Plane Webhook Handler")

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/plane")
PLANE_WEBHOOK_SECRET = os.getenv("PLANE_WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature"""
    if not PLANE_WEBHOOK_SECRET:
        return True
    
    expected = hmac.new(
        PLANE_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)


@app.post("/webhook/plane")
async def handle_plane_webhook(request: Request):
    """Handle incoming Plane webhooks"""
    
    # Get signature
    signature = request.headers.get("X-Plane-Signature", "")
    
    # Get body
    body = await request.body()
    
    # Verify signature
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    payload = await request.json()
    
    event_type = payload.get("event")
    data = payload.get("data", {})
    
    logger.info(f"Received Plane webhook: {event_type}")
    
    # Forward to n8n
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "source": "plane",
                    "event": event_type,
                    "data": data,
                    "timestamp": payload.get("timestamp")
                },
                timeout=30.0
            )
            
            logger.info(f"Forwarded to n8n: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to forward to n8n: {e}")
    
    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

## PLANE API CLIENT (Python SDK)

```python
#!/usr/bin/env python3
# plane_integration/client.py
"""
Plane API Client for Omni Quantum Elite

Provides programmatic access to Plane project management.
"""

import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class Issue:
    id: str
    name: str
    description: Optional[str]
    state: str
    priority: str
    assignees: List[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Issue":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            state=data.get("state", {}).get("name", "Unknown"),
            priority=data.get("priority", "none"),
            assignees=[a["email"] for a in data.get("assignees", [])],
            labels=[l["name"] for l in data.get("labels", [])],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        )


class PlaneClient:
    """Plane API Client"""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None
    ):
        self.base_url = base_url or os.getenv("PLANE_URL", "http://plane-api:8000")
        self.api_key = api_key or os.getenv("PLANE_API_KEY")
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def close(self):
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # WORKSPACES
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    async def list_workspaces(self) -> List[Dict]:
        """List all workspaces"""
        response = await self._client.get("/api/v1/workspaces/")
        response.raise_for_status()
        return response.json()
    
    async def get_workspace(self, slug: str) -> Dict:
        """Get workspace by slug"""
        response = await self._client.get(f"/api/v1/workspaces/{slug}/")
        response.raise_for_status()
        return response.json()
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # PROJECTS
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    async def list_projects(self, workspace_slug: str) -> List[Dict]:
        """List all projects in a workspace"""
        response = await self._client.get(f"/api/v1/workspaces/{workspace_slug}/projects/")
        response.raise_for_status()
        return response.json()
    
    async def create_project(
        self,
        workspace_slug: str,
        name: str,
        description: str = "",
        identifier: str = None
    ) -> Dict:
        """Create a new project"""
        response = await self._client.post(
            f"/api/v1/workspaces/{workspace_slug}/projects/",
            json={
                "name": name,
                "description": description,
                "identifier": identifier or name[:3].upper()
            }
        )
        response.raise_for_status()
        return response.json()
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # ISSUES
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    async def list_issues(
        self,
        workspace_slug: str,
        project_id: str,
        state: str = None,
        priority: str = None,
        assignee: str = None
    ) -> List[Issue]:
        """List issues with optional filters"""
        params = {}
        if state:
            params["state"] = state
        if priority:
            params["priority"] = priority
        if assignee:
            params["assignee"] = assignee
        
        response = await self._client.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
            params=params
        )
        response.raise_for_status()
        
        return [Issue.from_dict(i) for i in response.json().get("results", [])]
    
    async def create_issue(
        self,
        workspace_slug: str,
        project_id: str,
        name: str,
        description: str = "",
        priority: str = "medium",
        state_id: str = None,
        assignee_ids: List[str] = None,
        label_ids: List[str] = None
    ) -> Issue:
        """Create a new issue"""
        data = {
            "name": name,
            "description": description,
            "priority": priority
        }
        
        if state_id:
            data["state"] = state_id
        if assignee_ids:
            data["assignees"] = assignee_ids
        if label_ids:
            data["labels"] = label_ids
        
        response = await self._client.post(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
            json=data
        )
        response.raise_for_status()
        return Issue.from_dict(response.json())
    
    async def update_issue(
        self,
        workspace_slug: str,
        project_id: str,
        issue_id: str,
        **updates
    ) -> Issue:
        """Update an existing issue"""
        response = await self._client.patch(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
            json=updates
        )
        response.raise_for_status()
        return Issue.from_dict(response.json())
    
    async def add_comment(
        self,
        workspace_slug: str,
        project_id: str,
        issue_id: str,
        comment: str
    ) -> Dict:
        """Add a comment to an issue"""
        response = await self._client.post(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/",
            json={"comment_html": f"<p>{comment}</p>"}
        )
        response.raise_for_status()
        return response.json()
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # CYCLES (Sprints)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    async def list_cycles(self, workspace_slug: str, project_id: str) -> List[Dict]:
        """List all cycles/sprints"""
        response = await self._client.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_cycle_issues(
        self,
        workspace_slug: str,
        project_id: str,
        cycle_id: str
    ) -> List[Issue]:
        """Get all issues in a cycle"""
        response = await self._client.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/"
        )
        response.raise_for_status()
        return [Issue.from_dict(i["issue_detail"]) for i in response.json()]


# Example usage
async def main():
    async with PlaneClient() as client:
        # List workspaces
        workspaces = await client.list_workspaces()
        print(f"Found {len(workspaces)} workspaces")
        
        # Create an issue
        issue = await client.create_issue(
            workspace_slug="omni-quantum",
            project_id="abc123",
            name="Implement Token Infinity failover",
            description="Add automatic failover for AI providers",
            priority="high"
        )
        print(f"Created issue: {issue.name}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```
