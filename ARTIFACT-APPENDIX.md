# Artifact Appendix
## Description
**Paper Title:** No Privacy for Privates: How Military Communities Experience and Perceive the Privacy Risks of Military-Marketed Mobile Apps

**Authors:** Joshua Shinkle, Chandrika Mukherjee, Abdullah Imran, Arjun Arunasalam, Donna Artusy, Antonio Bianchi, Z. Berkay Celik, Alexander Master

**Year:** 2026

**Requested Badge(s):** Available

**Artifact Description and Relevance:**
1. `keywords.txt` - The list of 55 military-related keywords used to query the Google Play Store for Military-Marketed Mobile Apps (MMMapps) to cultivate our dataset.
2. `mmmapp_dataset.csv` - The dataset of 242 MMMapps we analyzed to help answer our RQs.
3. `user_study_questionnaire.pdf` - The full user study questionnaire presented to participants to help us understand how military-affiliated personnel understand and attempt to mitigate the risks posed by MMMapps.
4. `user_study_response_data.md` - The per-question aggregated quantitative response data from the user study questionnaire, which helped us answer our RQs.
5. `quant_analysis.py` - The script used to calculate aggregated response data from the user study questionnaire, which helped us answer our RQs.
6. `first-party_code_provenance.py` - The script used to determine first-party code provenance from scraped Google Play developer info.
7. `survey_apps_representativeness.py` - The script used to verify that the MMMapps we presented in our user study were representative of the broader MMMapp dataset.
8. `behavior-uncomfortability_discrepancy.py` - The script used to assess the degree to which participants were using MMMapps that engage in data practices they find inappropriate.
9. `classifier_bert.py` - The script used to fine-tune and evaluate a BERT-based classifier that labels Google Play app descriptions as MMMapp or not, serving as a recall-prioritized filter to reduce manual review effort when collecting MMMapps.
10. `bert_model/` - The directory containing the fine-tuned BERT model weights and tokenizer files produced by classifier_bert.py.

### Security/Privacy Issues and Ethical Concerns
There are no security or privacy risks for the machine of the person opening/downloading our artifacts.

For the user study, we obtained IRB approval from our institution prior to conducting any data collection. The permission to use the aggregated user study response data as an artifact was obtained through the user study consent form which states "We may share the anonymous data and findings with other researchers or in research papers or presentations."

## Environment
### Accessibility
All artifacts can be accessed at https://github.com/purseclab/no_privacy_for_privates.

## Notes on Reusability
1. The list of 55 military-related keywords can be reused in future work to cultivate relevant MMMapps datasets, as currently available MMMapps may be removed from app stores and new MMMapps may be released. This list can also be expanded in future work to target military communities of non-US countries.

2. The dataset of 242 MMMapps can be reused and extended in future work investigating security and privacy concerns posed by MMMapps.

3. The user study questionnaire could be extended and relevant parts reused to author additional studies (e.g., examining how perceptions evolve in response to institutional guidance or policy changes).

4. The aggregated user study response data could be reused in future work studying military communities (e.g., examining how perceptions evolve in response to institutional guidance or policy changes).

5. `quant_analysis.py` can be extended in future work interested in calculating and visualizing aggregated response data from user study questionnaires.

6. `first-party_code_provenance.py` can be reused in future work interested in the first-party code provenance of Android apps.

7. `survey_apps_representativeness.py` can be extended in future work to determine to what degree a subset of apps are representative of the data practices of a broader app dataset.

8. `behavior-uncomfortability_discrepancy.py` can be extended in future work to assess the degree to which participants are using apps that engage in data practices they find inappropriate.

9. `classifier_bert.py` can be reused or extended in future work interested in training text classifiers to filter candidate apps from large app-store query results based on their descriptions.

10. `bert_model/` can be reused in future work to directly apply our trained classifier to new app descriptions, or as a starting point for further fine-tuning on related app-classification tasks.