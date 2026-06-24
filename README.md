# No Privacy for Privates
This repository contains artifacts for the paper: "*No Privacy for Privates: How Military Communities Experience and Perceive the Privacy Risks of Military-Marketed Mobile Apps*" accepted at the 26th Privacy Enhancing Technologies Symposium (PETS).

# Abstract
A subset of mobile applications is explicitly marketed to military-affiliated personnel. These Military-Marketed Mobile Apps (MMMapps) collect privacy-sensitive data using the same mechanisms as general-purpose apps. However, when such data belongs to military-affiliated personnel, it may be exploited by malicious actors in ways that threaten personal safety, unit operations, and national security. Despite these risks, the data practices and code provenance of MMMapps, as well as how this population perceives and attempts to mitigate these risks, remain poorly understood. In this paper, we address this gap by combining large-scale app analysis with a user study. We first curate a dataset of 242 MMMapps and leverage app analysis techniques to characterize their data practices and code provenance. Then, we conduct a user study with n=103 military-affiliated participants in the United States to examine which data practices and code provenance characteristics they consider inappropriate, what threat scenarios they believe those practices enable, and which mitigations they view as most effective.

Our results show that MMMapps frequently exhibit data practices and code provenance characteristics that are misaligned with the privacy expectations of military-affiliated personnel. For instance, 40% of MMMapps collect more data than they disclose in their privacy labels or data safety sections. 83.5% of our study participants report using at least one MMMapp that engages in data practices they are uncomfortable with. Additionally, although military-affiliated personnel are generally concerned about third-party libraries accessing their data, 64% of MMMapps include third-party SDKs, some developed in countries perceived as adversarial by a majority of the participants. Overall, our findings reveal a substantial misalignment between the privacy expectations of military-affiliated personnel and the data practices and software supply chains of MMMapps. We propose recommendations at the federal, DoD, app store, and device levels to improve privacy risk mitigation for this at-risk population.

# Artifact Description and Relevance
1. `keywords.txt` - The list of 55 military-related keywords used to query the Google Play Store for Military-Marketed Mobile Apps (MMMapps) to cultivate our dataset.

2. `llm_classifier_binary.py` - The script used to implement the binary LLM-as-a-Judge classifier, prompting GPT-4 to label each app description as MMMapp (1) or not (0) and scoring its agreement against human-labeled data. 

3. `llm_classifier_decimal.py` - The script used to implement the range LLM-as-a-Judge classifier, prompting GPT-4 to assign each app description a continuous 0-to-1 score reflecting its likelihood of being an MMMapp.

4. `classifier_bert.py` - The script used to fine-tune and evaluate a BERT-based classifier that labels Google Play app descriptions as MMMapp or not, serving as a recall-prioritized filter to reduce manual review effort when collecting MMMapps. 

5. `bert_model/` - The directory containing the fine-tuned BERT model weights and tokenizer files produced by classifier_bert.py.

6. `llm_classifier_reddit.py` - The script used to extract candidate app names mentioned in Reddit posts, bodies, and comments by prompting GPT-4 over text retrieved via the Reddit API, supporting discovery of additional MMMapps beyond keyword search.

7. `mmmapp_dataset.csv` - The dataset of 242 MMMapps we analyzed to help answer our RQs.

8. `mobsf_static_only.py` - The script used to run MobSF static analysis on MMMapp APKs and extract their permissions, trackers, third-party and native libraries, URLs, and domains into structured reports.

9. `ui_crawler_avc.py` - The script used to automatically crawl an MMMapp's user interface to discover and log on-screen fields that request personally identifiable information (PII) from military-affiliated users. 

10. `network_analysis_zap.py` - The script used to capture an MMMapp's runtime network traffic through OWASP ZAP and analyze it for transmitted PII, location indicators, and first- versus third-party destinations. 

11. `first-party_code_provenance.py` - The script used to determine first-party code provenance from scraped Google Play developer info.

12. `data_safety_scraper_driver.js` - The driver script that reads a list of package names from a CSV and invokes `data_safety_scraper_module.js` to batch-collect the Google Play Data Safety section data for each MMMapp.

13. `data_safety_scraper_module.js` - The module used to fetch and parse the Data Safety section (shared data, collected data, security practices, and privacy policy URL) from a Google Play app listing.

14. `apple_privacy_scraper.py` - The script used to scrape the privacy nutrition label data (data collection sections, purposes, categories, and items) for MMMapps from their Apple App Store listings.

15. `survey_apps_representativeness.py` - The script used to verify that the MMMapps we presented in our user study were representative of the broader MMMapp dataset.

16. `user_study_questionnaire.pdf` - The full user study questionnaire presented to participants to help us understand how military-affiliated personnel understand and attempt to mitigate the risks posed by MMMapps.

17. `user_study_response_data.md` - The per-question aggregated quantitative response data from the user study questionnaire, which helped us answer our RQs.

18. `quant_analysis.py` - The script used to calculate aggregated response data from the user study questionnaire, which helped us answer our RQs.

19. `behavior-uncomfortability_discrepancy.py` - The script used to assess the degree to which participants were using MMMapps that engage in data practices they find inappropriate.