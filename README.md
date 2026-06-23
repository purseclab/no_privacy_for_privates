# No Privacy for Privates
This repository contains artifacts for the paper: "*No Privacy for Privates: How Military Communities Experience and Perceive the Privacy Risks of Military-Marketed Mobile Apps*" accepted at the 26th Privacy Enhancing Technologies Symposium (PETS).

# Abstract
A subset of mobile applications is explicitly marketed to military-affiliated personnel. These Military-Marketed Mobile Apps (MMMapps) collect privacy-sensitive data using the same mechanisms as general-purpose apps. However, when such data belongs to military-affiliated personnel, it may be exploited by malicious actors in ways that threaten personal safety, unit operations, and national security. Despite these risks, the data practices and code provenance of MMMapps, as well as how this population perceives and attempts to mitigate these risks, remain poorly understood. In this paper, we address this gap by combining large-scale app analysis with a user study. We first curate a dataset of 242 MMMapps and leverage app analysis techniques to characterize their data practices and code provenance. Then, we conduct a user study with n=103 military-affiliated participants in the United States to examine which data practices and code provenance characteristics they consider inappropriate, what threat scenarios they believe those practices enable, and which mitigations they view as most effective.

Our results show that MMMapps frequently exhibit data practices and code provenance characteristics that are misaligned with the privacy expectations of military-affiliated personnel. For instance, 40% of MMMapps collect more data than they disclose in their privacy labels or data safety sections. 83.5% of our study participants report using at least one MMMapp that engages in data practices they are uncomfortable with. Additionally, although military-affiliated personnel are generally concerned about third-party libraries accessing their data, 64% of MMMapps include third-party SDKs, some developed in countries perceived as adversarial by a majority of the participants. Overall, our findings reveal a substantial misalignment between the privacy expectations of military-affiliated personnel and the data practices and software supply chains of MMMapps. We propose recommendations at the federal, DoD, app store, and device levels to improve privacy risk mitigation for this at-risk population.

# Artifact Description and Relevance
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