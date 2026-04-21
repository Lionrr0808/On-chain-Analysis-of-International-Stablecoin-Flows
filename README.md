# On-chain Analysis of International Stablecoin Flows
  Estimate stablecoin flows across five major regions (North America, Asia &amp; Pacific, Europe, Latin America &amp; Caribbean, Africa &amp; Middle East) using open-source tools and publicly accessible blockchain data, reproducing and simplifying the methodology presented in Reuter (2025).

## Publicly Available Data

### Blockchain Data
For the first stage of the project, I will focus on Ethereum transactions. If the result shows significant regional bias, I will try to further collect Binance Smart Chain data or other available blockchain data.

> **Note:** The reference paper obtained full copies of transaction data on different blockchains, but this requires large storage and computational power, which may not be feasible for a UROP project.

**Estimated data volume:** 350k – 700k (7 days of Ethereum transaction data over $10)

### ENS Domains
Converting hexadecimal addresses to human-readable domain names

### CEX Wallet Labels
Used to link wallets to regional exchanges (not mentioned in the “Data” part of the reference paper, but is accessible using GitHub dataset)  
- Example: [https://github.com/ethereum-lists/ethereum-lists](https://github.com/ethereum-lists/ethereum-lists)

### GDP Data & Exchange Rates
Used for analysis with economic drivers, accessible using World Bank API & Yahoo Finance API

## Methodology

### Blockchain Data Collection
Three methods are available for data collection. I will choose **BigQuery** as my primary method to attain blockchain data.

### Domain Name Conversion
Using `web3` library in Python, we can convert hexadecimal addresses into human-readable domain names.

### Generating Region Labels for Training Dataset
**Target:** 3,000–5,000 reliably labeled wallets, requiring analysis of approximately 50,000–100,000 ENS domains.

- **ENS Domain Name Analysis**  
  Rule-based language detection: Python `langdetect` or `cld3` library  
  LLM API (DeepSeek or Gemini)

- **Regional Exchange Interaction**  
  Compile a list of centralized exchanges with clear regional focus  
  Obtain their deposit wallet addresses from public sources (e.g., GitHub)  
  For a wallet to be labeled as a certain region, >90% of its CEX interactions must be with exchanges focused on that region

- **Time Zone Activity Filtering (for validation)**  
  For each candidate wallet from Methods A/B, compute hourly transaction distribution  
  Convert UTC timestamps to each potential region's "typical" time zone  
  If the wallet shows no clear nighttime dip in its presumed region's time zone, flag as uncertain  
  Only keep wallets where the activity pattern matches the expected region

### Feature Extraction
Using Python `pandas` functions.

- **Temporal Features (from `block_timestamp`)**  
  Hourly Activity Distribution  
  Daylight saving time pattern  
  Polynomial fit coefficients  
  Weekend vs. weekday ratio

- **Counterparty Features**  
  Top 5 CEX  
  CEX interaction share  
  Top 10 ERC-20 / BEP-20 Tokens  
  ***Need additional data including CEX address list, contract labels***

- **Transaction Behavior Features (from `value` & transaction count)**  
  Average transaction value  
  Median transaction value  
  Transaction count  
  Total volume  
  Maximum transaction value  
  First activity date  
  Unique counterparties count

### Model Training

- **Model Selection:** Gradient Boosted Decision Tree  
- **Method:** Yggdrasil Decision Forests in Python  
- **Training Process**  
  - **Level 1:** Classify into macro-groups sharing similar time zones  
    - Group A: North America, Latin America (UTC-8 to UTC-3)  
    - Group B: Europe, Africa & Middle East (UTC+0 to UTC+3)  
    - Group C: Asia & Pacific (UTC+5 to UTC+10)  
  - **Level 2:** Distinguish regions within each macro-group using non-temporal features  
- **Handling Class Imbalances**  
  Balance class weights: Each sample is weighed inversely proportional to its class frequency

### Estimating International Stablecoin Flows

- For transactions between **self-custodial wallets**: estimate the stablecoin inflows, outflows, and within-flows for each region, and calculate the net flows  
- For transactions between **wallets and CEX**: identify all CEX wallets and allocate CEX flows based on the distribution of counterparty regions for each CEX
