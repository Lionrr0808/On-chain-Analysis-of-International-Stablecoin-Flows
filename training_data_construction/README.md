# Training Data Labeling Methodology

## Overview

The training data was labeled using two independent methods. Only addresses where both methods agreed on the label were selected for the final training set, with an additional filter of transaction amount > 30.

---

## Labeling Methods

### Method 1: CEX Interaction Labeling

- **Rule**: If over 90% of a wallet's CEX (Centralized Exchange) interactions originate from the same region, the wallet is labeled with that region.
- **Data Source**: CEX interaction patterns and their associated regions.

### Method 2: Domain Name Analysis (LLM-based)

ENS domain names were classified using a Large Language Model (DeepSeek-V4-Flash) with the following prompt:

#### System Prompt

You are trained to classify ENS domain names into regions. Output ONLY a single digit 0-5.

#### User Prompt Template

You are trained to classify ENS domain names into the following regions:
{{"Latin America and Caribbean"(1),"North America"(2),"Africa and Middle East"(3),"Europe"(4),"Asia and Pacific"(5),"Unclassified"(0)}}.
Use the number after each region as the output.

Consider references to:

Language (e.g., Chinese pinyin, Spanish, French, English)

Cultures (e.g., music, sports, memes)

Localities (city names, landmarks)

Memes and internet culture

Be creative and mindful of:

Language commonly used in crypto and Web3

Languages spoken in multiple regions (e.g., English, French, Spanish)

If you cannot classify into any of the 5 regions, classify it as "Unclassified" (0).

Domain: {domain}

Output ONLY the number (0-5):

---

## Data Selection Criteria

Only addresses meeting **both** conditions were included in the final training set:

1. **Label Agreement**: The region label from CEX interaction matches the label from domain name analysis.
   Or domain name label with stricter prompt and restrictions (e.g. temp = 0.01)
2. **Transaction Activity**: Total transaction amount > 30.

---

## Label Encoding

| Code | Region |
|:----:|:-------|
| 0 | Unclassified |
| 1 | Latin America and Caribbean |
| 2 | North America |
| 3 | Africa and Middle East |
| 4 | Europe |
| 5 | Asia and Pacific |

---

## Output

The final training data is saved as `final_training_data.csv`, containing:
- All original feature columns
- `final_label` (numeric code)
- `final_label_name` (region name)
