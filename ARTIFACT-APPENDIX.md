# Artifact Appendix
## Description
**Paper Title:** No Privacy for Privates: How Military Communities Experience and Perceive the Privacy Risks of Military-Marketed Mobile Apps

**Authors:** Joshua Shinkle, Chandrika Mukherjee, Abdullah Imran, Arjun Arunasalam, Donna Artusy, Antonio Bianchi, Z. Berkay Celik, Alexander Master

**Year:** 2026

**Requested Badge(s):** Available

**Artifact Description and Relevance:**
1. `keywords.txt` - The list of 55 military-related keywords used to query the Google Play Store for Military-Marketed Mobile Apps (MMMapps) to cultivate our dataset.

2. `initial_app_name_collection.py` - The script used to perform the initial collection of MMMapp candidates by querying the Google Play Store with each of the 55 military-related keywords and aggregating the returned app listings into a deduplicated set.

3. `llm_classifier_binary.py` - The script used to implement the binary LLM-as-a-Judge classifier, prompting GPT-4 to label each app description as MMMapp (1) or not (0) and scoring its agreement against human-labeled data. 

4. `llm_classifier_decimal.py` - The script used to implement the range LLM-as-a-Judge classifier, prompting GPT-4 to assign each app description a continuous 0-to-1 score reflecting its likelihood of being an MMMapp.

5. `classifier_bert.py` - The script used to fine-tune and evaluate a BERT-based classifier that labels Google Play app descriptions as MMMapp or not, serving as a recall-prioritized filter to reduce manual review effort when collecting MMMapps. 

6. `bert_model/` - The directory containing the fine-tuned BERT model weights and tokenizer files produced by classifier_bert.py.

7. `llm_classifier_reddit.py` - The script used to extract candidate app names mentioned in Reddit posts, bodies, and comments by prompting GPT-4 over text retrieved via the Reddit API, supporting discovery of additional MMMapps beyond keyword search.

8. `mmmapp_dataset.csv` - The dataset of 242 MMMapps we analyzed to help answer our RQs.

9. `mobsf_static_only.py` - The script used to run MobSF static analysis on MMMapp APKs and extract their permissions, trackers, third-party and native libraries, URLs, and domains into structured reports.

10. `ui_crawler_avc.py` - The script used to automatically crawl an MMMapp's user interface to discover and log on-screen fields that request personally identifiable information (PII) from military-affiliated users. 

11. `network_analysis_zap.py` - The script used to capture an MMMapp's runtime network traffic through OWASP ZAP and analyze it for transmitted PII, location indicators, and first- versus third-party destinations. 

12. `first-party_code_provenance.py` - The script used to determine first-party code provenance from scraped Google Play developer info.

13. `data_safety_scraper_driver.js` - The driver script that reads a list of package names from a CSV and invokes `data_safety_scraper_module.js` to batch-collect the Google Play Data Safety section data for each MMMapp.

14. `data_safety_scraper_module.js` - The module used to fetch and parse the Data Safety section (shared data, collected data, security practices, and privacy policy URL) from a Google Play app listing.

15. `apple_privacy_scraper.py` - The script used to scrape the privacy nutrition label data (data collection sections, purposes, categories, and items) for MMMapps from their Apple App Store listings.

16. `survey_apps_representativeness.py` - The script used to verify that the MMMapps we presented in our user study were representative of the broader MMMapp dataset.

17. `user_study_questionnaire.pdf` - The full user study questionnaire presented to participants to help us understand how military-affiliated personnel understand and attempt to mitigate the risks posed by MMMapps.

18. `user_study_response_data.md` - The per-question aggregated quantitative response data from the user study questionnaire, which helped us answer our RQs.

19. `quant_analysis.py` - The script used to calculate aggregated response data from the user study questionnaire, which helped us answer our RQs.

20. `behavior-uncomfortability_discrepancy.py` - The script used to assess the degree to which participants were using MMMapps that engage in data practices they find inappropriate.


### Security/Privacy Issues and Ethical Concerns
There are no security or privacy risks for the machine of the person opening/downloading our artifacts.

For the user study, we obtained IRB approval from our institution prior to conducting any data collection. The permission to use the aggregated user study response data as an artifact was obtained through the user study consent form which states "We may share the anonymous data and findings with other researchers or in research papers or presentations."



## Environment
### Accessibility
All artifacts can be accessed at https://github.com/purseclab/no_privacy_for_privates.

## Notes on Reusability
1. `keywords.txt` can be reused in future work to cultivate relevant MMMapps datasets, as currently available MMMapps may be removed from app stores and new MMMapps may be released. This list can also be expanded in future work to target military communities of non-US countries.

2. `initial_app_name_collection.py` can be reused or extended in future work interested in seeding an app dataset by programmatically querying the Google Play Store with a list of keywords.

3. `llm_classifier_binary.py` can be reused or extended in future work interested in using LLMs to perform binary classification of apps from their store descriptions.

4. `llm_classifier_decimal.py` can be reused or extended in future work interested in using LLMs to produce continuous, thresholdable relevance scores for apps from their store descriptions.

5. `classifier_bert.py` can be reused or extended in future work interested in training text classifiers to filter candidate apps from large app-store query results based on their descriptions.

6. `bert_model/` can be reused in future work to directly apply our trained classifier to new app descriptions, or as a starting point for further fine-tuning on related app-classification tasks.

7. `llm_classifier_reddit.py` can be reused or extended in future work interested in using LLMs to mine app mentions from social media discussions.

8. `mmmapp_dataset.csv` can be reused and extended in future work investigating security and privacy concerns posed by MMMapps.
`mobsf_static_only.py` can be reused or extended in future work interested in batch static analysis of Android apps to characterize their permissions, libraries, and embedded trackers.

9. `mobsf_static_only.py` can be reused or extended in future work interested in batch static analysis of Android apps to characterize their permissions, libraries, and embedded trackers.

10. `ui_crawler_avc.py` can be extended in future work interested in automatically discovering PII-requesting input fields in Android app interfaces.

11. `network_analysis_zap.py` can be reused or extended in future work interested in dynamically analyzing the network behavior of Android apps to detect PII exfiltration and third-party data flows.

12. `first-party_code_provenance.py` can be reused in future work interested in the first-party code provenance of Android apps.

13. `data_safety_scraper_driver.js` can be extended in future work interested in batch-collecting Data Safety disclosures across a large set of Android apps.

14. `data_safety_scraper_module.js` can be reused in future work interested in extracting structured Data Safety section disclosures from Google Play apps.

15. `apple_privacy_scraper.py` can be reused or extended in future work interested in collecting and structuring Apple App Store privacy label data at scale.

16. `survey_apps_representativeness.py` can be extended in future work to determine to what degree a subset of apps are representative of the data practices of a broader app dataset.

17. `user_study_questionnaire.pdf` can be extended and relevant parts reused to author additional studies (e.g., examining how perceptions evolve in response to institutional guidance or policy changes).

18. `user_study_response_data.md` can be reused in future work studying military communities (e.g., examining how perceptions evolve in response to institutional guidance or policy changes).

19. `quant_analysis.py` can be extended in future work interested in calculating and visualizing aggregated response data from user study questionnaires.

20. `behavior-uncomfortability_discrepancy.py` can be extended in future work to assess the degree to which participants are using apps that engage in data practices they find inappropriate.