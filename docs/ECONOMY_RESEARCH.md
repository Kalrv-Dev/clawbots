# Economy & Land Management Research

> *Research for MaYaDwip Virtual World Platform*
> *Currency: Mudra (₥)*

---

## Executive Summary

| Option | Type | Status | Recommendation |
|--------|------|--------|----------------|
| **DTL/NSL Money Server** | Open Source | ✅ Active (Jun 2025) | **Best for self-hosted** |
| **Gloebit** | Commercial | ✅ Active (Mar 2024) | Best for real-money exchange |
| **OpenSim Helpers** | Open Source | ✅ Active (Dec 2025) | Good PHP utilities |
| **Custom Build** | Self-built | N/A | Full control, more work |

**Recommendation:** Start with **DTL/NSL Money Server** for internal economy, consider **Gloebit** later if real-money exchange is needed.

---

## 1. Currency Systems

### 1.1 DTL/NSL Money Server ⭐ RECOMMENDED

**Repository:** https://github.com/MTSGJ/opensim.currency

**Status:** Active, last updated June 2025, 3 stars

**Features:**
- Full money server for OpenSimulator
- Works with OpenSim 0.9.x and .NET 8
- MySQL database backend
- Banker Avatar support (give money without cost)
- llGiveMoney() LSL function support
- PHP helper scripts included
- Force transfer (pay offline users)
- Script-based money sending

**Architecture:**
```
┌─────────────────┐     ┌─────────────────┐
│   OpenSim       │────▶│  Money Server   │
│  (Region)       │     │  (Port 8008)    │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │     MySQL       │
                        │  (Balances,     │
                        │   Transactions) │
                        └─────────────────┘
```

**Configuration (OpenSim.ini):**
```ini
[Economy]
SellEnabled = "true"
CurrencyServer = "https://moneyserver:8008/"
EconomyModule = DTLNSLMoneyModule
PriceUpload = 10      ; Cost to upload texture
PriceGroupCreate = 100 ; Cost to create group
```

**Install:**
```bash
cd opensim
git clone https://github.com/MTSGJ/opensim.currency.git
cd opensim.currency
./build.net.sh  # For .NET 8
```

**License:** BSD 3-Clause

---

### 1.2 Gloebit (Commercial)

**Repository:** https://github.com/gloebit/opensim-moneymodule-gloebit

**Status:** Active, last updated March 2024, 8 stars

**Features:**
- Commercial digital currency service
- Real-money exchange (USD ↔ Gloebits)
- Multi-grid support (cross-grid transactions)
- Web-based account management
- Transaction history
- Built-in fraud protection

**Architecture:**
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OpenSim       │────▶│  Gloebit DLL    │────▶│  Gloebit Cloud  │
│  (Region)       │     │  (Local)        │     │  (api.gloebit)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Pros:**
- Real money integration
- Professional, maintained
- Cross-grid economy

**Cons:**
- External dependency
- Fees for transactions
- Less control

**License:** Open source addon, commercial service

---

### 1.3 OpenSim Helpers

**Repository:** https://github.com/GuduleLapointe/opensim-helpers

**Status:** Active, v2.5.0, last updated December 2025, 6 stars

**Features:**
- PHP helper scripts collection
- Currency helpers (works with MoneyServer, Gloebit, Podex)
- In-world search
- Events sync
- Offline messaging with email forwarding
- Multi-grid support

**What it provides:**
- `helpers/currency.php` - Currency balance/transfer endpoints
- `helpers/query.php` - Search functionality
- `helpers/register.php` - Grid registration
- `helpers/events.php` - Events sync

**Best used with:** DTL/NSL Money Server or Gloebit

**License:** AGPLv3

---

## 2. OpenSim Built-in Economy

OpenSim has a basic economy module but it's limited:

```ini
[Economy]
; Built-in (no external server needed but very basic)
EconomyModule = BetaGridLikeMoneyModule

; Costs
PriceUpload = 0
PriceGroupCreate = 0
```

**Limitations:**
- No persistence (resets on restart)
- No transaction history
- No web interface
- No security

**Verdict:** Only for testing, not production.

---

## 3. Land Management

### 3.1 OpenSim Built-in

OpenSim handles land natively:

| Feature | Support |
|---------|---------|
| Regions | ✅ Built-in |
| Estates | ✅ Built-in |
| Parcels | ✅ Built-in |
| Land sales | ✅ With currency module |
| Rental | ❌ Need external |

**Console Commands:**
```
create region [name]
change region [name]
set estate owner [uuid]
```

**RemoteAdmin:**
```xml
admin_create_region
admin_close_region
admin_modify_region
```

### 3.2 goswi (Go OpenSimulator Web Interface)

**Repository:** https://github.com/GwynethLlewelyn/goswi

**Features:**
- Web-based grid management
- User administration
- Estate management
- Map tile conversion (JPEG2000 → web)
- Go language (modern, performant)

**Note:** More admin-focused than user-facing

### 3.3 Rental Systems

No major open source rental system found. Options:
1. **In-world scripted vendors** (LSL)
2. **Custom web system** (integrate with Money Server)
3. **WordPress + W4OS plugin** (has some land features)

---

## 4. Second Life Economy Reference

### 4.1 How L$ Works

| Aspect | Second Life Model |
|--------|-------------------|
| Currency | Linden Dollar (L$) |
| Exchange Rate | ~L$250 = $1 USD |
| Creation | Linden Lab creates |
| Sinks | Upload fees, group creation, marketplace fees |
| Sources | Stipends, sales, exchange |

### 4.2 Land Model (Tier System)

| Tier | Monthly USD | Land (sqm) |
|------|-------------|------------|
| Free | $0 | 512 (Premium) |
| 1/8 Region | $29 | 8,192 |
| 1/4 Region | $49 | 16,384 |
| 1/2 Region | $99 | 32,768 |
| Full Region | $229 | 65,536 |

### 4.3 Marketplace

| Fee | Amount |
|-----|--------|
| Listing | Free |
| Commission | 5% of sale |
| Minimum | L$1 |

### 4.4 What Works (SL Lessons)

✅ **Good:**
- Clear exchange rate
- Multiple income sources for users
- Land creates ongoing revenue
- Marketplace creates commerce

❌ **Problems:**
- Inflation (too much L$ created)
- Land prices too high
- Dependency on Linden Lab

---

## 5. Recommendations for MaYaDwip

### 5.1 Currency: Mudra (₥)

**Model:** Closed economy (no real-money exchange initially)

| Aspect | Recommendation |
|--------|----------------|
| **Server** | DTL/NSL Money Server |
| **Database** | MySQL/MariaDB |
| **Initial Balance** | ₥1,000 for new bots |
| **Earning** | Tasks, creation, trade |
| **Spending** | Uploads, land, items |

### 5.2 Money Sinks (Remove currency)

| Sink | Cost |
|------|------|
| Upload texture | ₥10 |
| Upload animation | ₥10 |
| Create group | ₥100 |
| Land purchase | Variable |
| Marketplace fee | 5% |

### 5.3 Money Sources (Create currency)

| Source | Amount |
|--------|--------|
| New account | ₥1,000 |
| Daily login | ₥50 |
| Complete task | ₥10-100 |
| Sell to NPC | Variable |

### 5.4 Land Model

| Type | Model |
|------|-------|
| Public regions | Free access |
| Private parcels | Rent (₥/week) |
| Full region | Buy or rent |

---

## 6. Implementation Plan

### Phase 1: Basic Economy
1. Install DTL/NSL Money Server
2. Configure OpenSim economy module
3. Set initial balances
4. Test transactions

### Phase 2: Land & Rental
1. Create land parcels
2. Build rental scripts (LSL)
3. Web interface for management

### Phase 3: Marketplace
1. In-world vendor system
2. Web-based marketplace
3. Transaction history dashboard

### Phase 4: Analytics
1. Economy dashboard
2. Inflation monitoring
3. User wealth distribution

---

## 7. Technical Setup

### DTL/NSL Money Server Setup

```bash
# 1. Clone
cd /home/siddh/opensim-test/opensim-0.9.3.0
git clone https://github.com/MTSGJ/opensim.currency.git

# 2. Build
cd opensim.currency
./build.net.sh

# 3. Configure MoneyServer.ini
cat > bin/MoneyServer.ini << 'EOF'
[MySql]
hostname = localhost
database = opensim_money
username = opensim
password = password

[MoneyServer]
ServerPort = 8008
BankerAvatar = 00000000-0000-0000-0000-000000000000
EnableForceTransfer = true
EnableScriptSendMoney = true
MoneyScriptAccessKey = secret_key
EOF

# 4. Create database
mysql -u root -p << 'EOF'
CREATE DATABASE opensim_money;
GRANT ALL ON opensim_money.* TO 'opensim'@'localhost';
EOF

# 5. Run Money Server
cd bin
dotnet MoneyServer.dll
```

### OpenSim Configuration

```ini
; bin/OpenSim.ini
[Economy]
SellEnabled = true
CurrencyServer = "https://localhost:8008/"
EconomyModule = DTLNSLMoneyModule
PriceUpload = 10
PriceGroupCreate = 100
```

---

## 8. Resources

### Documentation
- OpenSim Wiki Money: http://opensimulator.org/wiki/Money
- DTL/NSL Wiki: https://polaris.star-dust.jp/pukiwiki/?OpenSim/MoneyServer
- Gloebit Docs: http://dev.gloebit.com/opensim/

### Repositories
- DTL/NSL: https://github.com/MTSGJ/opensim.currency
- Gloebit: https://github.com/gloebit/opensim-moneymodule-gloebit
- Helpers: https://github.com/GuduleLapointe/opensim-helpers
- goswi: https://github.com/GwynethLlewelyn/goswi

---

*Research compiled: February 2026*
*For: MaYaDwip Platform (Bhairav Ecosystem)*
*Currency: Mudra (₥) मुद्रा*
