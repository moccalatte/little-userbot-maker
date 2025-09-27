# Little Userbot Maker – PRD (Updated)

## Purpose & Business Model

- **Goal**: Platform bisnis SaaS untuk layanan userbot Telegram dengan subscription model
- **Target Market**: Power users, automation enthusiasts, dan reseller yang butuh userbot automation tanpa technical complexity
- **Revenue Model**: Monthly/yearly subscription untuk akses userbot service
- **Success Metrics**: User retention >80%, subscription conversion >15%, system uptime >99.5%

## Arsitektur 2-VPS

### VPS A: Bot Wizard (Frontend)
**Lokasi**: Public-facing server dengan domain dan SSL
**Fungsi**:
- Interface registrasi dan onboarding customer
- Session creation (OTP dan QR login)
- Payment processing dan subscription management
- Customer support dan monitoring dashboard

### VPS B: Userbot Service (Backend)
**Lokasi**: Private server dengan high resource untuk automation
**Fungsi**:
- Menjalankan multiple userbot instances
- Command processing dan automation
- Rate limiting dan abuse detection
- Data storage dan analytics

### Communication Flow
```
[Customer] → [Telegram Bot] → [Bot Wizard VPS] → [API] → [Userbot Service VPS] → [Telegram API]
```

## Core Components

### Bot Wizard (VPS A)
- **Registration Flow**: `/start` → phone verification → subscription selection → payment
- **Session Creation**: Dual method (OTP/QR) dengan 2FA support dan retry logic
- **Subscription Management**: Plan selection, payment integration, renewal reminders
- **Session Delivery**: Encrypted session transmission ke userbot service via API
- **Customer Dashboard**: Status monitoring, usage statistics, billing history

### Userbot Service (VPS B)  
- **Multi-User Engine**: Concurrent userbot instances dengan resource isolation
- **Command System**: Extensible command framework (`!help`, `!sg`, `!gg`, `!scr`, `!rg`)
- **API Endpoints**: RESTful API untuk session management dan monitoring
- **Subscription Enforcement**: Automatic start/stop berdasarkan subscription status
- **Analytics Engine**: Usage tracking, command statistics, performance metrics

## Business Subscription Plans

### Starter Plan ($9.99/month)
- 1 userbot instance
- Basic commands (`!help`, `!gg`, `!sg`)
- 50 broadcasts/day
- Email support

### Pro Plan ($19.99/month)  
- 3 userbot instances
- All commands including scraping
- 500 broadcasts/day
- Priority support
- Custom schedules

### Enterprise Plan ($49.99/month)
- 10 userbot instances
- Unlimited commands dan broadcasts  
- Custom integrations
- Dedicated support
- API access

## Technical Architecture

### Database Schema (PostgreSQL - Shared)
```sql
-- Users dan subscription management
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    subscription_plan TEXT,  -- 'starter', 'pro', 'enterprise'
    subscription_start TIMESTAMP,
    subscription_end TIMESTAMP,
    payment_status TEXT,     -- 'active', 'pending', 'expired'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Session storage dengan encryption
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_string TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT true,
    metadata JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage analytics
CREATE TABLE usage_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    command_type TEXT,
    execution_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    date DATE DEFAULT CURRENT_DATE
);
```

### API Contracts

#### Bot Wizard → Userbot Service
```json
POST /api/v1/sessions
{
    "user_id": 123456789,
    "username": "user123",
    "session_string": "encrypted_base64_session",
    "subscription_plan": "pro",
    "subscription_start": "2024-01-01T00:00:00Z",
    "subscription_end": "2024-02-01T00:00:00Z"
}
```

#### Subscription Status Check
```json  
GET /api/v1/users/{user_id}/status
Response: {
    "user_id": 123456789,
    "status": "active|expired|suspended",
    "plan": "pro",
    "expires_at": "2024-02-01T00:00:00Z",
    "usage_stats": {
        "commands_today": 45,
        "broadcasts_today": 12
    }
}
```

## Revenue & Scaling Strategy

### Phase 1: MVP Launch (Month 1-3)
- Deploy kedua VPS dengan basic functionality
- 100 beta users dengan free trial
- Payment gateway integration (Stripe/PayPal)
- Basic customer support

### Phase 2: Growth (Month 4-12)
- Marketing campaign (Telegram channels, forums)
- Referral program (1 bulan gratis per referral)
- Advanced features (custom commands, integrations)
- Target: 1000 paying subscribers

### Phase 3: Scale (Year 2+)
- Multi-region deployment
- Enterprise features (API, webhooks)
- Reseller program (white-label)  
- Target: 10,000+ subscribers

### Revenue Projections
```
Month 6:  500 users × $15 avg = $7,500/month
Month 12: 1000 users × $18 avg = $18,000/month
Year 2:   5000 users × $20 avg = $100,000/month
```

## Security & Compliance

### Data Protection
- Session encryption dengan user-specific keys
- PCI DSS compliance untuk payment processing
- Regular security audits dan penetration testing
- GDPR compliance untuk EU users

### Rate Limiting & Abuse Prevention
- Command rate limits per subscription plan
- IP-based rate limiting untuk bot wizard
- Automated abuse detection dan account suspension
- Telegram flood protection dengan exponential backoff

### Monitoring & Alerting
- System health monitoring (Prometheus/Grafana)
- Error tracking dan logging (Sentry)
- Performance metrics dan SLA monitoring
- Automated failover untuk high availability

## Operational Procedures

### Customer Onboarding
1. User starts bot → phone verification
2. Plan selection dan payment processing
3. Session creation (guided wizard)
4. Automatic service activation dalam 5 menit
5. Welcome email dengan tutorial dan support links

### Support Workflow  
- Tier 1: Bot-based FAQ dan troubleshooting
- Tier 2: Human support via Telegram/email
- Tier 3: Technical escalation untuk complex issues
- SLA: <2 hours response untuk Pro+, <24h untuk Starter

### Billing & Renewals
- Automated billing 3 days sebelum expiry
- Grace period 7 hari dengan service suspension warning
- Automatic service termination setelah 14 hari non-payment
- Win-back campaigns untuk churned users

## Risk Management

### Technical Risks
- **Telegram API changes**: Monitor official announcements, maintain compatibility layer
- **VPS downtime**: Multi-region backup, automated failover procedures
- **Scale bottlenecks**: Horizontal scaling plan, load balancing implementation

### Business Risks
- **Competition**: Focus pada user experience dan unique features
- **Legal issues**: Legal review untuk ToS, compliance dengan Telegram ToS
- **Payment fraud**: Implement fraud detection, manual review untuk high-value transactions

### Mitigation Strategies
- Regular backups dan disaster recovery testing
- Legal insurance dan compliance monitoring
- Financial reserves untuk 6-month operation
- Clear refund policy dan dispute resolution

## Success Criteria

### Month 3 (MVP)
- ✅ 100 beta users dengan positive feedback
- ✅ <5% churn rate
- ✅ 99% uptime untuk core services
- ✅ Break-even pada operational costs

### Month 6 (Growth)
- 🎯 500 paying subscribers  
- 🎯 $7,500 MRR (Monthly Recurring Revenue)
- 🎯 Customer satisfaction >4.5/5
- 🎯 <1% fraud rate

### Year 1 (Scale)
- 🎯 1000+ paying subscribers
- 🎯 $18,000+ MRR
- 🎯 Profitability setelah all costs
- 🎯 Team expansion (2-3 employees)

## Rollout Plan

### Pre-Launch (Week 1-2)
- Deploy bot wizard VPS dengan domain dan SSL
- Deploy userbot service VPS dengan monitoring
- Setup PostgreSQL database dengan replication
- Configure payment gateway dan billing system

### Beta Launch (Week 3-4)  
- Invite 50 selected beta users
- Collect feedback dan iterate
- Fix critical bugs dan performance issues
- Document support procedures

### Public Launch (Month 2)
- Marketing campaign launch
- Public bot availability  
- Customer support team ready
- Analytics dan monitoring active

### Post-Launch (Month 3+)
- Weekly feature releases
- Monthly business reviews
- Quarterly scaling evaluations
- Continuous security audits

---

*Dokumen ini adalah panduan strategis untuk implementasi Little Userbot Maker sebagai platform bisnis SaaS. Review dan update secara berkala sesuai market feedback dan technical evolution.*