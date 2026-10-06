"""
Subscription Offerings (Python reference).

ACP supports subscriptions (recurring) and discoverable resources.
This module defines subscription offerings that turn VP Earner
into an agent-as-a-service micro-SaaS.
"""


# Subscription offerings (recurring revenue model)
SUBSCRIPTION_OFFERINGS = [
    {
        "id": "crypto-intel-subscription",
        "name": "30-Day Crypto Intelligence Subscription",
        "type": "subscription",
        "priceUSDC": 25,
        "billingCycle": "monthly",
        "description": "Daily market briefs, token research, protocol comparison, and risk reports",
        "features": [
            "Daily DeFi TVL briefs",
            "Token research reports (2/week)",
            "Protocol security updates",
            "Risk assessment scores",
        ],
        "slaHours": 24,
        "category": "market-intel",
        "autoRenew": True,
        "gracePeriodDays": 3,
    },
    {
        "id": "security-monitor-subscription",
        "name": "Dependency Security Monitoring (Monthly)",
        "type": "subscription",
        "priceUSDC": 15,
        "billingCycle": "monthly",
        "description": "Weekly dependency vulnerability scans with automated alerts",
        "features": [
            "Weekly npm/pip audit scans",
            "Vulnerability alerts (critical/high)",
            "SBOM generation",
            "Remediation recommendations",
        ],
        "slaHours": 48,
        "category": "dependency-security-audit",
        "autoRenew": True,
        "gracePeriodDays": 3,
    },
]


# Discoverable resources (agent-as-a-service endpoints)
DISCOVERABLE_RESOURCES = [
    {
        "id": "get_token_risk_score",
        "name": "Token Risk Score",
        "type": "resource",
        "description": "Evaluate token security, distribution, and risk metrics",
        "inputSchema": {
            "tokenAddress": {"type": "string", "required": True},
            "chain": {"type": "string", "enum": ["base", "ethereum"], "default": "base"},
        },
        "estimatedCost": 0.05,
    },
    {
        "id": "check_dependency_vulnerability",
        "name": "Dependency Vulnerability Check",
        "type": "resource",
        "description": "Check if package dependencies have known vulnerabilities",
        "inputSchema": {
            "packageJson": {"type": "string", "required": True},
        },
        "estimatedCost": 0.10,
    },
    {
        "id": "analyze_repository",
        "name": "Repository Analysis",
        "type": "resource",
        "description": "Full code quality + security analysis of a GitHub repo",
        "inputSchema": {
            "repoUrl": {"type": "string", "required": True},
            "depth": {"type": "string", "enum": ["quick", "full"], "default": "quick"},
        },
        "estimatedCost": 0.50,
    },
    {
        "id": "market_sentiment_snapshot",
        "name": "Market Sentiment Snapshot",
        "type": "resource",
        "description": "Get AI agent market sentiment and narrative analysis",
        "inputSchema": {
            "query": {"type": "string", "required": True},
            "sources": {"type": "array", "items": {"type": "string"},
                       "default": ["coingecko", "defillama", "messari"]},
        },
        "estimatedCost": 0.15,
    },
]


def is_subscription_job(job: dict) -> bool:
    """Check if a job is for a subscription renewal."""
    return job.get("offerType") == "subscription"


def is_resource_job(job: dict) -> bool:
    """Check if a job is for a discoverable resource call."""
    return job.get("offerType") == "resource"


def subscription_ltv(sub: dict) -> float:
    """
    Calculate LTV (lifetime value) of a subscription.
    Used in scoring to prioritize recurring revenue over one-off jobs.
    """
    monthly = sub.get("priceUSDC", 0)
    retention_rate = 0.8
    expected_months = 1 / (1 - retention_rate) if sub.get("autoRenew") else 1
    return monthly * expected_months
